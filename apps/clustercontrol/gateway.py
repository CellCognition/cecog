"""
                           The CellCognition Project
                     Copyright (c) 2006 - 2010 Michael Held
                      Gerlich Lab, ETH Zurich, Switzerland
                              www.cellcognition.org

              CellCognition is distributed under the LGPL License.
                        See trunk/LICENSE.txt for details.
                 See trunk/AUTHORS.txt for author contributions.
"""

"""
Simple PyAMF-based web-service controlling the cluster scheduler via a DRMAA 1.0
(http://www.drmaa.org/) interface.
"""

__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL$'

__all__ = []

#-------------------------------------------------------------------------------
# standard library imports:
#
import socket, \
       os, \
       sys

#-------------------------------------------------------------------------------
# extension module imports:
#
import pyamf
import drmaa

from pdk.fileutils import safe_mkdirs

#-------------------------------------------------------------------------------
# cecog imports:
#
import cecog.batch
from cecog import (JOB_CONTROL_RESUME,
                   JOB_CONTROL_SUSPEND,
                   JOB_CONTROL_TERMINATE,
                   )

#-------------------------------------------------------------------------------
# constants:
#
# map DRMAA status codes to readable text
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

# map cecog job actions to DRMAA
DRMAA_CONTROL_ACTIONS = {
    JOB_CONTROL_RESUME : drmaa.JobControlAction.RESUME,
    JOB_CONTROL_SUSPEND : drmaa.JobControlAction.SUSPEND,
    JOB_CONTROL_TERMINATE : drmaa.JobControlAction.TERMINATE,
    }

#-------------------------------------------------------------------------------
# functions:
#
def parse_args(args):
    """
    Parse commandline options.
    """
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('--host', dest='host', default='localhost',
                      help='The host address for the AMF gateway')
    parser.add_option('-p', '--port', dest='port', default=8080,
                      help='The port number the server uses')

    return parser.parse_args(args)


def cecog_job_template(jt, path_out, args, emails, is_bulk_job=False):
    job_name = 'cecog_batch_analyzer'
    env_variables = ['PYTHONPATH', 'PATH', 'LD_LIBRARY_PATH']

    jt.jobName = job_name
    jt.workingDirectory = cecog.batch.__path__[0]
    print jt.workingDirectory
    jt.jobEnvironment = dict([(x, os.environ[x]) for x in env_variables])
    print jt.jobEnvironment
    jt.remoteCommand = sys.executable
    print jt.remoteCommand
    jt.args = ['batch.py'] + args
    jt.joinFiles = True

    jt.email = emails
    jt.nativeSpecification = '-m bea'

    path_out_cluster = os.path.join(path_out, 'log_cluster')
    safe_mkdirs(path_out_cluster)
    path_out_cluster = ':' + path_out_cluster
    if is_bulk_job:
        jt.outputPath = path_out_cluster
        # FIXME: another DRMAA hack: the PARAMETRIC_INDEX is NOT resolved in args!
        jt.args += ['--cluster_index', 'SGE_TASK_ID']#drmaa.JobTemplate.PARAMETRIC_INDEX]
    else:
        jt.outputPath = path_out_cluster
    return jt

#-------------------------------------------------------------------------------
# classes:
#
class ClusterControl(object):

    def __init__(self):
        self._session = drmaa.Session()
        self._session.initialize()

    def __del__(self):
        self._session.exit()

    def submit_job(self, job_type, settings, path_out, emails, nr_items=1):

        # FIXME: hack converting Windows paths
        path_out = str(path_out.replace('\\','/'))
        settings = settings.replace('\\','/')
        path_out = os.path.normpath(path_out)
        path_out_settings = os.path.join(path_out, 'settings')
        print path_out_settings
        safe_mkdirs(path_out_settings)

        filename_settings = os.path.join(path_out_settings, 'cecog_settings.conf')
        f = file(filename_settings, 'w')
        f.write(settings)
        f.close()

        args = ['-s', filename_settings]

        is_bulk_job = True if nr_items > 1 else False

        jt = self._session.createJobTemplate()
        jt = cecog_job_template(jt, path_out, args, emails, is_bulk_job)

        if is_bulk_job:
            job_id = self._session.runBulkJobs(jt, 1, nr_items, 1)
        else:
            job_id = self._session.runJob(jt)
        print job_id
        return job_id

    def control_job(self, job_id, action):
        self._check_jobid(job_id)
        self._session.control(job_id, DRMAA_CONTROL_ACTIONS[action])

    def get_job_status(self, job_id):
        self._check_jobid(job_id)
        return DRMAA_STATUS_TEXT[self._session.jobStatus(job_id)]

    def get_service_info(self):
        return "Service on %s up and running. (Scheduler: %s, DRMAA %s)" %\
               (socket.gethostname(), self._session.drmsInfo,
                self._session.version)

    def _check_jobid(self, job_id):
        if job_id is None:
            raise ValueError("Invalid job ID '%s'!" % job_id)

#-------------------------------------------------------------------------------
# main:
#
if __name__ == '__main__':
    import sys
    from pyamf.remoting.gateway.wsgi import WSGIGateway
    from wsgiref import simple_server

    options = parse_args(sys.argv[1:])[0]
    service = {'clustercontrol': ClusterControl(),
               }

    host = options.host
    port = int(options.port)

    gw = WSGIGateway(service)

    httpd = simple_server.WSGIServer(
        (host, port),
        simple_server.WSGIRequestHandler,
    )

    httpd.set_app(gw)

    print 'Started server on http://%s:%s' % (host, port)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

