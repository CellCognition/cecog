import sys, \
       os, \
       re, \
       time, \
       pickle

from optparse import OptionParser

path_command = 'cd /g/software/linux/pack/cellcognition-1.2.4/SRC/cecog_git/pysrc/scripts/EMBL/projects'
command = 'python-2.7 test_compression.py -i /g/mitocheck/Thomas/mitocheck_links/ -o /g/mitocheck/Thomas/compression/out --id %s'

array_script_name = 'compression'
script_dir = '/g/mitocheck/Thomas/compression/scripts'

job_size = 8
filename_id_list = '/g/mitocheck/Thomas/spotlist.txt'

hours = 4
minutes = 0

if __name__ == "__main__":
    
    if not os.path.isdir(script_dir):
        os.makedirs(script_dir)
    pbs_out_dir = '/g/mitocheck/PBS/%s' % array_script_name
    if not os.path.isdir(pbs_out_dir):
        os.makedirs(pbs_out_dir)
        
    head = """#!/bin/bash
#PBS -l walltime=%02i:%02i:00
#PBS -M twalter@embl.de
#PBS -m e
#PBS -o /g/mitocheck/PBS/%s
#PBS -e /g/mitocheck/PBS/%s
""" % (hours, minutes, array_script_name, array_script_name)
    
    fp = open(filename_id_list, 'r')
    id_list = [x.strip() for x in fp.readlines()]
    fp.close()
    
    N = len(id_list)
    indices = [[j + i for j in range(min(job_size, N-i))] for i in range(0, N, job_size)]
    jobCount = 1
    for index_set in indices:
        id_subset = [id_list[i] for i in index_set]
        print id_subset
        cmd = path_command + '\n'
        for id in id_subset:
            cmd += (command % id) + '\n'
            
        script_name = '%s%i.sh' % (os.path.join(script_dir, array_script_name), jobCount)            
        script_file = open(script_name, "w")
        script_file.write(head + cmd)
        script_file.close()            
        os.system('chmod a+rwx %s' % script_name)
        
        jobCount += 1
        
    # create main file to be submitted to the pbs server.
    main_script_name = '%s_main.sh' % os.path.join(script_dir, array_script_name)
    main_script_file = file(main_script_name, 'w')
    main_content = """#!/bin/bash
#PBS -J 1-%i
#PBS -q clng_new
#PBS -M twalter@embl.de
#PBS -m e
#PBS -o /g/mitocheck/PBS/%s
#PBS -e /g/mitocheck/PBS/%s
%s$PBS_ARRAY_INDEX.sh
"""
    main_content %= (jobCount, array_script_name, array_script_name, os.path.join(script_dir, array_script_name))
    main_script_file.write(main_content)
    os.system('chmod a+rwx %s' % main_script_name)
    
    sub_cmd = '/usr/pbs/bin/qsub -q clng_new -J 1-%i %s' % (jobCount, main_script_name)
    print sub_cmd
    print 'array containing %i jobs' % jobCount
    #os.system(sub_cmd)
        
    print "* total positions: ", jobCount
