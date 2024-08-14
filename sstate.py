#!/bin/env python3

import argparse
import subprocess
import re
from tabulate import tabulate


# This function converts MB to larger units
def human_readable(num, suffix='B'):
    for unit in ['Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--partition", help="Specify partition (standard, gpu, largemem, debug, standard-oc). "
                                                  "If this is not specified all nodes will be shown")
    args = parser.parse_args()
    return args

# This function will take the scontrol output and reformat the node data into a list of kv pairs
# This will allow for better parsing/filtering of the node data later in the script
def reformat_scontrol_output(scontrol_output, node_data_list=[]):
    scontrol_output = scontrol_output.splitlines()
    for node_output in scontrol_output:
        temp_data_list = []
        node = re.split(r"(\w+=)", node_output)
        for element, line in enumerate(node):
            if re.match(r"(\w+=)", line):
                temp_data_list.append("{0}{1}".format(node[element], node[element+1]))
        node_data_list.append(temp_data_list)
    return node_data_list

# This function will filter out unwanted nodes if a partition is specified
def filter_partition_node_data(node_data_list, partition_node_data_list=[]):
    for node in node_data_list:
        for line in node:
            if line.split("=")[0].strip() == "Partitions":
                if args.partition == "debug":
                    if line.split("=")[1].strip() != "debug":
                        continue
                    else:
                        partition_node_data_list.append(node)
                else:
                    for partition in line.split("=")[1].split(","):
                        if args.partition.lower() == partition.strip():
                            partition_node_data_list.append(node)
    return partition_node_data_list

# This function will parse through node data to get available, allocated, and total resources
# It will also calculate some resource averages and usage percents, as well as print output
def parse_node_data(node_data_list):
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

    overall_alloc_gpu = 0
    overall_available_gpu = 0
    overall_total_gpu = 0

    # Loop through each node and gather scontrol info on them
    # This will also get resources and calculate resource totals and averages
    for node in node_data_list:
        overall_node += 1
        for line in node:
            key = line.split("=")[0].strip()
            value = line.split("=")[1].strip()
            gpu_tot = 'N/A'
            gpu_alloc = 'N/A'
            percent_used_gpu = 'N/A'

            # Changes values based on key
            if key == "NodeName":
                node_name = value           
            elif key == "CPUAlloc":
                try:
                    cpu_alloc = int(value)
                    overall_alloc_cpu += cpu_alloc
                except ValueError:
                    cpu_alloc = 0
                    overall_alloc_cpu += cpu_alloc
            elif key == "CPUTot":
                try:
                    cpu_tot = int(value)
                    overall_total_cpu += cpu_tot
                except ValueError:
                    cpu_tot = 0
                    overall_total_cpu += cpu_tot
            elif key == "CPULoad":
                try:
                    cpu_load = float(value)
                    overall_cpu_load += cpu_load
                except ValueError:
                    cpu_load = float(0)
                    overall_cpu_load += cpu_load
            elif key == "RealMemory":
                try:
                    total_mem = int(value)
                    overall_total_mem += total_mem
                except ValueError:
                    total_mem = 0
                    overall_total_mem += total_mem
            elif key == "AllocMem":
                try:
                    alloc_mem = int(value)
                    overall_alloc_mem += alloc_mem
                except ValueError:
                    alloc_mem = 0
                    overall_alloc_mem += alloc_mem
            elif key == "State":
                node_state = value
            elif key == "CfgTRES":
                # If there is gpu data, gets the total number of gpus
                if "gres/gpu" in line:
                    try:
                        gpu_tot = int(line.split(",")[-1].split("=")[1])
                        overall_total_gpu += gpu_tot
                    except ValueError:
                        gpu_tot = 0
                        overall_total_gpu += gpu_tot
            elif key == "AllocTRES":
                # If there is gpu data, get the allocated number of gpus
                if "gres/gpu" in line:
                    try:
                        gpu_alloc = int(line.split(",")[-1].split("=")[1])
                        overall_alloc_gpu += gpu_alloc
                    except ValueError:
                        gpu_alloc = 0
                        overall_alloc_gpu += gpu_alloc
        # Calculates percent used for cpu
        percent_used_cpu = 0
        if cpu_tot > 0:
            percent_used_cpu = cpu_alloc / cpu_tot * 100

        # Calculates available cpus
        cpu_avail = cpu_tot
        if cpu_alloc != 0:
            cpu_avail = cpu_tot - cpu_alloc

        # Calculates percent used for memory
        percent_used_mem = 0
        if total_mem > 0:
            percent_used_mem = alloc_mem / total_mem * 100

        # Calculates available memory
        avail_mem = total_mem
        if alloc_mem != 0:
            avail_mem = total_mem - alloc_mem

        # If there are GPUs but none are allocated, sets GPU allocated to 0
        if type(gpu_alloc) is str and type(gpu_tot) is int:
            gpu_alloc = 0
        # Calculates percent used for GPU
        if type(gpu_alloc) is int and type(gpu_tot) is int:
            percent_used_gpu = gpu_alloc / gpu_tot * 100

        # Calculates available gpus
        gpu_avail = gpu_tot
        if gpu_alloc != "N/A" and gpu_alloc != 0:
            gpu_avail = gpu_tot - gpu_alloc

        # Adjust available resources based on full allocated resources
        if cpu_alloc == cpu_tot:
            avail_mem = 0
            if gpu_alloc != "N/A":
                gpu_avail = 0
        if alloc_mem == total_mem:
            cpu_avail = 0
            if gpu_alloc != "N/A":
                gpu_avail = 0
        if gpu_alloc != "N/A":
            if gpu_alloc == gpu_tot:
                cpu_avail = 0
                avail_mem = 0

        # Calculate the available resources
        overall_available_cpu += cpu_avail
        overall_available_mem += avail_mem
        if gpu_avail != "N/A":
            overall_available_gpu += gpu_avail

        # Swaps the allocated memory, total memory, and available memory to a human readable format for the table
        alloc_mem = human_readable(alloc_mem)
        total_mem = human_readable(total_mem)
        avail_mem = human_readable(avail_mem)

        rows.append([node_name, cpu_alloc, cpu_avail, cpu_tot, percent_used_cpu, cpu_load, alloc_mem, avail_mem, total_mem, percent_used_mem,
                     gpu_alloc, gpu_avail, gpu_tot, percent_used_gpu, node_state])

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

    # Calculates the overall percent used for gpu
    overall_percent_used_gpu = 'N/A'
    if overall_total_gpu > 0:
        overall_percent_used_gpu = overall_alloc_gpu / overall_total_gpu * 100

    # Prints a table with the node statistics
    print(tabulate(rows, headers=['Node', 'AllocCPU', 'AvailCPU', 'TotalCPU', 'PercentUsedCPU', 'CPULoad', 'AllocMem', 'AvailMem', 'TotalMem',
                                  'PercentUsedMem', 'AllocGPU', 'AvailGPU', 'TotalGPU', 'PercentUsedGPU', 'NodeState'], floatfmt=".2f"))

    print("\nTotals:")

    # Prints the overall statistics
    print(tabulate([[overall_node, overall_alloc_cpu, overall_available_cpu, overall_total_cpu, overall_percent_used_cpu, overall_cpu_load,
                    overall_alloc_mem, overall_available_mem, overall_total_mem, overall_percent_used_mem, overall_alloc_gpu,
                    overall_available_gpu, overall_total_gpu, overall_percent_used_gpu]],
                   headers=['Node', 'AllocCPU', 'AvailCPU', 'TotalCPU', 'PercentUsedCPU', 'CPULoad', 'AllocMem', 'AvailMem', 'TotalMem',
                            'PercentUsedMem', 'AllocGPU', 'AvailGPU', 'TotalGPU', 'PercentUsedGPU'], floatfmt=".2f"))

if __name__ == '__main__':
    # Parse command line arguments
    args = parse_args()

    # Get node data via scontrol and reformat it for easier usability
    scontrol_output = subprocess.check_output("/usr/bin/scontrol show nodes --oneliner", shell=True).decode()
    node_data_list = reformat_scontrol_output(scontrol_output)

    # If a partition is specified, filter out unwanted nodes from reformatted scontrol output
    if args.partition:
        node_data_list = filter_partition_node_data(node_data_list)

    # Parse through the node data to get available, allocated, and total resources
    # This will also calculate some resource averages and usage percents, as well as print output
    parse_node_data(node_data_list)