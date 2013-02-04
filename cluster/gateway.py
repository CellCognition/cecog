"""
                           The CellCognition Project
        Copyright (c) 2006 - 2012 Michael Held, Christoph Sommer
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

import os
from os.path import dirname, abspath, join
import sys

import pyamf
import drmaa

#FIXME - remove all CECOG PYTHONPATHS from bash profiles!
cecog_root = dirname(abspath(__file__)).split(os.sep)[:-1]
cecog_root = join(os.sep.join(cecog_root), "pysrc")
sys.path.append(cecog_root)

from cecog.util.util import makedirs
import cecog.batch
from cecog import (VERSION,
                   JOB_CONTROL_RESUME,
                   JOB_CONTROL_SUSPEND,
                   JOB_CONTROL_TERMINATE)


DRMAA_STATUS_TEXT = {
    drmaa.JobState.UNDETERMINED : 'process status cannot be determined',
    drmaa.JobState.QUEUED_ACTIVE : 'job is queued and active',
    drmaa.JobState.SYSTEM_ON_HOLD : 'job is queued and in system hold',
    drmaa.JobState.USER_ON_HOLD : 'job is queued and in user hold',
    drmaa.JobState.USER_SYSTEM_ON_HOLD : 'job is queued and in user and system '
                                         'hold',
    drmaa.JobState.RUNNING : 'job is running',
    drmaa.JobState.SYSTEM_SUSPENDED : 'job is system suspended',
    drmaa.JobState.USER_SUSPENDED : 'job is user suspended',
    drmaa.JobState.DONE : 'job finished normally',
    drmaa.JobState.FAILED : 'job finished, but failed',
    }

DRMAA_CONTROL_ACTIONS = {
    JOB_CONTROL_RESUME : drmaa.JobControlAction.RESUME,
    JOB_CONTROL_SUSPEND : drmaa.JobControlAction.SUSPEND,
    JOB_CONTROL_TERMINATE : drmaa.JobControlAction.TERMINATE,
    }

CECOG_VERSIONS_PATH = '/clusterfs/gerlich/cecog_versions'
CECOG_DEFAULT_VERSION = '1.4.0'

def parse_args(args):
    """Parse commandline options."""
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('--host', dest='host', default='localhost',
                      help='The host address for the AMF gateway')
    parser.add_option('-p', '--port', dest='port', default=8080,
                      help='The port number the server uses')

    return parser.parse_args(args)


def cecog_job_template(jt, path_out, args, emails, version, batch_size=1,
                       is_bulk_job=False):
    job_name = 'cecog_batch_analyzer'
    env_variables = ['PATH', 'LD_LIBRARY_PATH']

    base_path = os.path.join(CECOG_VERSIONS_PATH, version)
    batch_path = os.path.join(base_path, 'pysrc', 'cecog', 'batch')

    jt.jobName = job_name
    jt.workingDirectory = batch_path
    print jt.workingDirectory

    # I want the almost the same environment as for the gateway!
    if os.environ.has_key('PYTHONPATH'):
        os.environ["PYTHONPATH"] = os.path.join(base_path, "pysrc")+os.pathsep+ \
            os.environ["PYTHONPATH"]
    else:
        os.putenv("PYTHONPATH", os.path.join(base_path, "pysrc"))

    jt.jobEnvironment = os.environ
    print jt.jobEnvironment
    jt.remoteCommand = os.path.join(batch_path, 'python')
    print jt.remoteCommand
    jt.args = ['batch.py'] + args
    jt.joinFiles = True

    jt.email = emails
    jt.nativeSpecification = '-m bea'

    path_out_cluster = os.path.join(path_out, 'log_cluster')
    makedirs(path_out_cluster)
    path_out_cluster = ':' + path_out_cluster
    if is_bulk_job:
        jt.outputPath = path_out_cluster
        # FIXME: another DRMAA hack: the PARAMETRIC_INDEX is NOT resolved in args!
        jt.args += ['--cluster_index', 'SGE_TASK_ID',
                    '--batch_size', str(batch_size)]
    else:
        jt.outputPath = path_out_cluster
    return jt


class ClusterControl(object):

    def __init__(self):
        self._session = drmaa.Session()
        self._session.initialize()

    def __del__(self):
        self._session.exit()

    def submit_job(self, job_type, settings, path_out, emails, nr_items=1,
                   batch_size=1, version=CECOG_DEFAULT_VERSION):
        path_out = str(path_out.replace('\\', '/'))
        settings = settings.replace('\\', '/')
        path_out = os.path.normpath(path_out)
        path_out_settings = os.path.join(path_out, 'settings')
        makedirs(path_out_settings)
        filename_settings = os.path.join(path_out_settings, 'cecog_settings.conf')
        f = file(filename_settings, 'w')
        f.write(settings)
        f.close()

        args = ['-s', filename_settings]

        # adjust the number of job items according to the batch size
        nr_items = int(nr_items / batch_size)
        # for modulo > 0 add one more item for the rest
        if nr_items % batch_size > 0:
            nr_items += 1

        is_bulk_job = True #if nr_items > 1 else False

        jt = self._session.createJobTemplate()
        jt = cecog_job_template(jt, path_out, args, emails, version,
                                batch_size, is_bulk_job)

        if is_bulk_job:
            job_id = self._session.runBulkJobs(jt, 1, nr_items, 1)
        else:
            job_id = self._session.runJob(jt)
        print job_id
        return job_id

    def control_job(self, job_id, action):
        self._check_jobid(job_id)
        job_ids = str(job_id).split(',')
        print 'control_job', job_ids, action
        for job_id in job_ids:
            self._session.control(job_id, DRMAA_CONTROL_ACTIONS[action])

    def get_job_status(self, job_id):
        self._check_jobid(job_id)
        job_ids = str(job_id).split(',')
        print 'get_job_status', job_ids
        status = {}
        for job_id in job_ids:
            s = DRMAA_STATUS_TEXT[self._session.jobStatus(job_id)]
            if not s in status:
                status[s] = 0
            status[s] += 1
        return ", ".join(["%s (%dx)" % (k, v) for k, v in status.iteritems()])

    def get_service_info(self):
        return "Service up and running. Scheduler: %s, cecog versions: %s" % \
               (self._session.drmsInfo, ', '.join(self.get_cecog_versions()))

    def get_cecog_versions(self):
        """Returns a list of supported cecog versions."""
        names = [n for n in os.listdir(CECOG_VERSIONS_PATH)
                 if os.path.isdir(os.path.join(CECOG_VERSIONS_PATH, n))]
        return sorted(names)

    def _check_jobid(self, job_id):
        if job_id is None:
            raise ValueError("Invalid job ID '%s'!" % job_id)


if __name__ == '__main__':
    oldmask = os.umask(0o000)
    from pyamf.remoting.gateway.wsgi import WSGIGateway
    from wsgiref import simple_server

    options = parse_args(sys.argv[1:])[0]
    service = {'clustercontrol': ClusterControl()}

    host = options.host
    port = int(options.port)

    gw = WSGIGateway(service)

    httpd = simple_server.WSGIServer((host, port),
                                     simple_server.WSGIRequestHandler)

    httpd.set_app(gw)
    print 'Started server on http://%s:%s' %(host, port)
    httpd.serve_forever()
