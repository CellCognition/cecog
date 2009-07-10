import logging, \
       os, \
       shutil

from pylons import request, response, session
from pylons import tmpl_context as c
from pylons.controllers.util import abort, redirect_to

from pdk.util.fileutils import safeMkdirs

from classifier.lib.base import BaseController, render, session
#import classifier.model as model

log = logging.getLogger(__name__)

permanent_store = '/tmp/uploads/'

class UploaderController(BaseController):

    def index(self):
        myfile = request.POST['myfile']
        safeMkdirs(permanent_store)
        filename_new = os.path.join(permanent_store,
                                    myfile.filename.lstrip(os.sep))
        permanent_file = open(filename_new, 'w')
        shutil.copyfileobj(myfile.file, permanent_file)
        myfile.file.close()
        permanent_file.close()

        log.info("Successfully uploaded: '%s' to '%s'." % (myfile.filename, filename_new))

        return 'toll'
