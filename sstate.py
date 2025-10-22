#!/bin/env python3

import subprocess
import re
from typing import Optional

import typer
from tabulate import tabulate
from colorama import Fore, Back, Style, init
from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Create Typer app with -h enabled for help
app = typer.Typer(add_completion=False, context_settings={"help_option_names": ["-h", "--help"]})

## argparse removed: Typer CLI is now used

# This function converts MB to larger units using decimal (1000-based) conversion
def human_readable(num, suffix='B'):
    for unit in ['M','G','T','P','E','Z']:
        if abs(num) < 1000.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1000.0
    return "%.1f%s%s" % (num, 'Y', suffix)

# This function adds color coding to node states
def colorize_node_state(state):
    """
    Add color coding to node states:
    - idle: default
    - mixed: yellow
    - allocated: green
    - down/drain/fail: bold red
    Note: Any bad state takes precedence if combined (e.g., mixed+down -> bad).
    """
    state_lower = state.lower()
    
    # Bad states take precedence over others
    if any(bad_state in state_lower for bad_state in ['down', 'drain', 'fail', 'error']):
        return f"{Fore.RED}{Style.BRIGHT}{state}{Style.RESET_ALL}"
    elif 'allocated' in state_lower or 'alloc' in state_lower:
        return f"{Fore.GREEN}{state}{Style.RESET_ALL}"
    elif 'mixed' in state_lower:
        return f"{Fore.YELLOW}{state}{Style.RESET_ALL}"
    elif 'idle' in state_lower:
        return f"{state}"  # Default color
    else:
        # Default color for unknown states
        return f"{state}"

def format_percentage(percentage):
    """Format percentage with visual bar indicator"""
    if percentage == 0:
        color = Style.RESET_ALL  # 0% is default (no color)
        bar_length = 0
    elif percentage >= 75:
        color = Fore.GREEN + Style.BRIGHT  # 75-100% is full (bright green)
        bar_length = 10
    elif percentage >= 50:
        color = Fore.CYAN  # 50-75% is high (cyan)
        bar_length = 8
    elif percentage >= 25:
        color = Fore.BLUE  # 25-50% is moderate (blue)
        bar_length = 6
    else:
        color = Fore.YELLOW  # 1-25% is low (yellow)
        bar_length = 4
    bar = "█" * min(int(percentage / 10), 10)
    return f"{color}{percentage:5.1f}%{Style.RESET_ALL} {color}{bar}{Style.RESET_ALL}"

def format_percentage_rich(percentage: float) -> Text:
    """Format percentage with visual bar indicator using Rich styles."""
    if percentage == 0:
        style = None
    elif percentage >= 75:
        style = "bold green"
    elif percentage >= 50:
        style = "cyan"
    elif percentage >= 25:
        style = "blue"
    else:
        style = "yellow"
    bar = "█" * min(int(percentage / 10), 10)
    txt = Text()
    txt.append(f"{percentage:5.1f}%", style=style)
    if bar:
        txt.append(" ")
        txt.append(bar, style=style)
    return txt

def print_section_header(title):
    """Print a styled section header"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'=' * 80}")
    print(f"{title:^80}")
    print(f"{'=' * 80}{Style.RESET_ALL}")

def create_colored_headers(headers):
    """Create colored table headers"""
    colored_headers = []
    for header in headers:
        colored_headers.append(f"{Fore.BLUE}{Style.BRIGHT}{header}{Style.RESET_ALL}")
    return colored_headers

def colorize_node_state_rich(state: str) -> Text:
    state_lower = state.lower()
    if any(bad_state in state_lower for bad_state in ['down', 'drain', 'fail', 'error']):
        return Text(state, style="bold red")
    elif 'allocated' in state_lower or 'alloc' in state_lower:
        return Text(state, style="green")
    elif 'mixed' in state_lower:
        return Text(state, style="yellow")
    else:
        return Text(state)

# This function will take the scontrol output and reformat the node data into a list of kv pairs
# This will allow for better parsing/filtering of the node data later in the script
def reformat_scontrol_output(scontrol_output, node_data_list=None):
    if node_data_list is None:
        node_data_list = []
    scontrol_output = scontrol_output.splitlines()
    for node_output in scontrol_output:
        temp_data_list = []
        node = re.split(r"([A-Z]\w+=)", node_output)
        for element, line in enumerate(node):
            if re.match(r"([A-Z]\w+=)", line):
                temp_data_list.append("{0}{1}".format(node[element], node[element+1]))
        node_data_list.append(temp_data_list)
    return node_data_list

# This function will filter out unwanted nodes if a partition is specified
def filter_partition_node_data(partition, node_data_list, partition_node_data_list=None):
    if partition_node_data_list is None:
        partition_node_data_list = []
    if not partition:
        return node_data_list
    for node in node_data_list:
        for line in node:
            if line.split("=")[0].strip() == "Partitions":
                if partition == "debug":
                    if line.split("=")[1].strip() != "debug":
                        continue
                    else:
                        partition_node_data_list.append(node)
                else:
                    for p in line.split("=")[1].split(","):
                        if partition.lower() == p.strip().lower():
                            partition_node_data_list.append(node)
    return partition_node_data_list

# This function will parse through node data to get available, allocated, and total resources
# It will also calculate some resource averages and usage percents, as well as print output
def parse_node_data(node_data_list, use_rich: bool = False, show_legend: bool = False):
    # Initializes variables to track resource values
    rows = []
    overall_node = 0
    overall_alloc_cpu = 0
    overall_available_cpu = 0
    overall_total_cpu = 0
    overall_cpu_load = 0

    overall_alloc_mem = 0
    overall_available_mem = 0
    overall_total_mem = 0

    # Setup Rich tables if requested
    if use_rich:
        node_table = Table(
            title=None,
            box=box.SIMPLE_HEAVY,
            show_lines=False,
            header_style="bold blue",
            pad_edge=False,
        )
        for col in ['Node', 'CPU', 'CPU Usage', 'CPULoad', 'Memory', 'Mem Usage', 'State']:
            node_table.add_column(col, overflow="fold")

    # Loop through each node and gather scontrol info on them
    # This will also get resources and calculate resource totals and averages
    for node in node_data_list:
        overall_node += 1

        # Initialize variables for each node to ensure numeric types
        node_name = ""
        cpu_alloc = 0
        cpu_tot = 0
        cpu_load = 0.0
        total_mem = 0
        alloc_mem = 0
        node_state = ""
        for line in node:
            key = re.split(r"([A-Z]\w+)(?==)", line)[1]
            value = re.split(r"([A-Z]\w+=)", line)[2]

            # Changes values based on key
            if key == "NodeName":
                node_name = value           
            elif key == "CPUAlloc":
                try:
                    cpu_alloc = int(value)
                except ValueError:
                    cpu_alloc = 0
                overall_alloc_cpu += cpu_alloc
            elif key == "CPUTot":
                try:
                    cpu_tot = int(value)
                except ValueError:
                    cpu_tot = 0
                overall_total_cpu += cpu_tot
            elif key == "CPULoad":
                try:
                    cpu_load = float(value)
                except ValueError:
                    cpu_load = 0.0
                overall_cpu_load += cpu_load
            elif key == "RealMemory":
                try:
                    total_mem = int(value)
                except ValueError:
                    total_mem = 0
                overall_total_mem += total_mem
            elif key == "AllocMem":
                try:
                    alloc_mem = int(value)
                except ValueError:
                    alloc_mem = 0
                overall_alloc_mem += alloc_mem
            elif key == "State":
                node_state = value

        # Calculates percent used for cpu
        percent_used_cpu = 0.0
        if cpu_tot > 0:
            percent_used_cpu = cpu_alloc / cpu_tot * 100.0

        # Calculates available cpus
        cpu_avail = cpu_tot
        if cpu_alloc != 0:
            cpu_avail = cpu_tot - cpu_alloc

        # Calculates percent used for memory
        percent_used_mem = 0.0
        if total_mem > 0:
            percent_used_mem = alloc_mem / total_mem * 100.0

        # Calculates available memory
        avail_mem = total_mem
        if alloc_mem != 0:
            avail_mem = total_mem - alloc_mem

        # Adjust available resources based on full allocated resources
        if cpu_alloc == cpu_tot:
            avail_mem = 0
        if alloc_mem == total_mem:
            cpu_avail = 0

        # Calculate the available resources
        overall_available_cpu += cpu_avail
        overall_available_mem += avail_mem

        # Save original numeric values for calculations, convert to human-readable for display
        alloc_mem_hr = human_readable(alloc_mem)
        total_mem_hr = human_readable(total_mem)
        avail_mem_hr = human_readable(avail_mem)

        # Prepare formatted values for readability
        formatted_cpu_usage = format_percentage(percent_used_cpu)
        formatted_mem_usage = format_percentage(percent_used_mem)
        formatted_cpu_load = f"{cpu_load:.2f}"
        formatted_node_state = colorize_node_state(node_state)

        if use_rich:
            cpu_display = f"{cpu_alloc}/{cpu_tot}"
            mem_display = f"{alloc_mem_hr}/{total_mem_hr}"
            node_table.add_row(
                node_name,
                cpu_display,
                format_percentage_rich(percent_used_cpu),
                formatted_cpu_load,
                mem_display,
                format_percentage_rich(percent_used_mem),
                colorize_node_state_rich(node_state),
            )
        else:
            # Append row with formatted values (tabulate path)
            rows.append([
                node_name,
                cpu_alloc,
                cpu_avail,
                cpu_tot,
                formatted_cpu_usage,
                formatted_cpu_load,
                alloc_mem_hr,
                avail_mem_hr,
                total_mem_hr,
                formatted_mem_usage,
                formatted_node_state
            ])

    # Calculates the overall percent used for cpu
    overall_percent_used_cpu = 0
    if overall_total_cpu > 0:
        overall_percent_used_cpu = overall_alloc_cpu / overall_total_cpu * 100

    # Calculates the average cpu load
    if overall_node > 0:
        overall_cpu_load = overall_cpu_load / overall_node

    # Calculates the overall percent used for mem
    overall_percent_used_mem = 0
    if overall_total_mem > 0:
        overall_percent_used_mem = overall_alloc_mem / overall_total_mem * 100

    # Swaps the overall allocated memory, total memory, and available memory to a human readable format for the table
    overall_alloc_mem = human_readable(overall_alloc_mem)
    overall_total_mem = human_readable(overall_total_mem)
    overall_available_mem = human_readable(overall_available_mem)

    if use_rich:
        console = Console()
        # Nodes table
        console.rule("[bold cyan]SLURM NODE STATUS")
        console.print(node_table)

        # Totals table
        console.rule("[bold cyan]CLUSTER TOTALS")
        totals_table = Table(box=box.SIMPLE_HEAVY, show_lines=False, header_style="bold blue", pad_edge=False)
        for col in ['Nodes', 'CPU', 'CPU Usage', 'AvgLoad', 'Memory', 'Mem Usage']:
            totals_table.add_column(col)
        cpu_totals_display = f"{overall_alloc_cpu}/{overall_total_cpu}"
        mem_totals_display = f"{overall_alloc_mem}/{overall_total_mem}"
        totals_table.add_row(
            str(overall_node),
            cpu_totals_display,
            format_percentage_rich(overall_percent_used_cpu),
            f"{overall_cpu_load:.2f}",
            mem_totals_display,
            format_percentage_rich(overall_percent_used_mem),
        )
        console.print(totals_table)

        # Legend (optional)
        if show_legend:
            console.print()
            console.print(Text("Legend:", style="bold cyan"))
            console.print("  0% usage - No color")
            console.print(Text("  █ Low usage (1-25%)", style="yellow"))
            console.print(Text("  █ Moderate usage (25-50%)", style="blue"))
            console.print(Text("  █ High usage (50-75%)", style="cyan"))
            console.print(Text("  █ Full usage (75-100%)", style="bold green"))
            console.print()
            console.print(Text("Node States:", style="cyan"))
            console.print("  idle - Available for jobs")
            console.print(Text("  mixed - Partially allocated", style="yellow"))
            console.print(Text("  allocated - Fully allocated", style="green"))
            console.print(Text("  down/drain/fail - Unavailable", style="bold red"))
        return
    else:
        # Tabulate-based output (existing default)
        print_section_header("SLURM NODE STATUS")
        headers = ['Node', 'AllocCPU', 'AvailCPU', 'TotalCPU', 'CPU Usage', 'CPULoad', 'AllocMem', 'AvailMem', 'TotalMem', 'Mem Usage', 'NodeState']
        colored_headers = create_colored_headers(headers)
        print(tabulate(rows, headers=colored_headers, tablefmt="grid", floatfmt=".2f"))

        print_section_header("CLUSTER TOTALS")
        totals_headers = ['Nodes', 'AllocCPU', 'AvailCPU', 'TotalCPU', 'CPU Usage', 'AvgLoad', 'AllocMem', 'AvailMem', 'TotalMem', 'Mem Usage']
        colored_totals_headers = create_colored_headers(totals_headers)
        totals_row = [
            overall_node,
            overall_alloc_cpu,
            overall_available_cpu,
            overall_total_cpu,
            format_percentage(overall_percent_used_cpu),
            f"{overall_cpu_load:.2f}",
            overall_alloc_mem,
            overall_available_mem,
            overall_total_mem,
            format_percentage(overall_percent_used_mem)
        ]
        print(tabulate([totals_row], headers=colored_totals_headers, tablefmt="grid", floatfmt=".2f"))
        print(f"\n{Fore.CYAN}{Style.BRIGHT}Legend:{Style.RESET_ALL}")
        print(f"  0% usage - No color")
        print(f"  {Fore.YELLOW}█ Low usage (1-25%){Style.RESET_ALL}")
        print(f"  {Fore.BLUE}█ Moderate usage (25-50%){Style.RESET_ALL}")
        print(f"  {Fore.CYAN}█ High usage (50-75%){Style.RESET_ALL}")
        print(f"  {Fore.GREEN}{Style.BRIGHT}█ Full usage (75-100%){Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}Node States:{Style.RESET_ALL}")
        print(f"  idle - Available for jobs")
        print(f"  {Fore.YELLOW}mixed{Style.RESET_ALL} - Partially allocated")
        print(f"  {Fore.GREEN}allocated{Style.RESET_ALL} - Fully allocated")
        print(f"  {Fore.RED}{Style.BRIGHT}down/drain/fail{Style.RESET_ALL} - Unavailable")

# Main function
@app.command()
def main(
    partition: Optional[str] = typer.Option(
        None,
        "--partition",
        "-p",
        help="Query specific partition. If this is not specified all nodes will be shown.",
        metavar="",
    ),
    rich_output: bool = typer.Option(
        True,
        "--rich/--no-rich",
        help="Use Rich tables for cleaner, more compact output.",
        show_default=True,
    ),
    show_legend: bool = typer.Option(
        False,
        "--legend/--no-legend",
        help="Show usage and state legend.",
        show_default=True,
    ),
):
    """Query node data in Slurm and present a color-coded summary."""

    # Get node data via scontrol and reformat it for easier usability
    scontrol_output = subprocess.check_output("$(/usr/bin/which scontrol) show nodes --oneliner", shell=True).decode()
    node_data_list = reformat_scontrol_output(scontrol_output)

    # If a partition is specified, filter out unwanted nodes from reformatted scontrol output
    if partition:
        node_data_list = filter_partition_node_data(partition, node_data_list)

    # Parse through the node data to get available, allocated, and total resources
    # This will also calculate some resource averages and usage percents, as well as print output
    parse_node_data(node_data_list, use_rich=rich_output, show_legend=show_legend)

# Execute main function
if __name__ == '__main__':
    app()
