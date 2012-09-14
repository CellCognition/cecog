import os, sys, time, re, pickle
import operator

from collections import OrderedDict

from scripts.EMBL.settings import Settings

from scripts.EMBL.utilities import *


class HTMLGenerator(object):
    def __init__(self, settings_filename=None, settings=None):
        if settings is None and settings_filename is None:
            raise ValueError("Either a settings object or a settings filename has to be given.")
        if not settings is None:
            self.oSettings = settings
        elif not settings_filename is None:
            self.oSettings = Settings(os.path.abspath(settings_filename), dctGlobals=globals())
        if not os.path.exists(self.oSettings.htmlDir):
            print 'making %s' % self.oSettings.htmlDir
            os.makedirs(self.oSettings.htmlDir)
        self.PLOT_HEIGHT = 202

    def getGraphFilenames(self, baseDir, plate, pos, feat_regex=None):
        if feat_regex is None:
            feat_regex = re.compile('.+')

        htmlDir = os.path.join(self.oSettings.htmlDir, plate, pos)

        graphPosDir = os.path.join(baseDir, plate, pos)
        track_filenames = sorted(os.listdir(graphPosDir))

        dctRelFilenames = {}
        for track_filename in track_filenames:
            searchObj = self.oSettings.track_id_regex.search(track_filename)
            featObj = feat_regex.search(track_filename)
            if not searchObj is None and not featObj is None:
                trackId = track_filename[searchObj.start():searchObj.end()]
                dctRelFilenames[trackId] = \
                    os.path.join(os.path.relpath(graphPosDir, htmlDir),
                                 track_filename)
        return dctRelFilenames

    def getPanelFilenames(self, plate, pos, panel):
        # primary_classification_panel--T00049__O0028.png
        # 'panel_classification--T00099__O0007--primary--primary.png'
        feat_regex = re.compile('(?P<panel>%s?)--(?P<rest>.+)\.png' % panel)
        dctRelFilenames = self.getGraphFilenames(self.oSettings.panelDir,
                                                 plate, pos,
                                                 feat_regex)

        return dctRelFilenames

    def getGalleryFilenames(self, plate, pos):
        dctRelFilenames = self.getGraphFilenames(self.oSettings.galleryDir,
                                                 plate, pos)
        return dctRelFilenames

    def getPlotFilenames(self, plate, pos, feature):
        feat_regex = re.compile('_(?P<feature>%s?)\.png' % feature)
        dctRelFilenames = self.getGraphFilenames(self.oSettings.singleCellPlotDir,
                                                 plate, pos, feat_regex)
        return dctRelFilenames

    def prepareDataForHTML(self, full_track_data, plate, pos,
                           lstTracks=None):
        if lstTracks is None:
            lstTracks = sorted(full_track_data[plate][pos].keys())

        res = {}
        for track in lstTracks:
            res[track] = {}
            for feature, proc_tuple in self.oSettings.value_extraction.iteritems():
                if len(proc_tuple) == 1:
                    res[track][feature] = full_track_data[plate][pos][track][proc_tuple[0]]
                elif len(proc_tuple) == 4:
                    res[track][feature] = proc_tuple[0](full_track_data[plate][pos][track][proc_tuple[1]][proc_tuple[2]][proc_tuple[3]])
                elif len(proc_tuple) == 7:
                    res[track][feature] = proc_tuple[0](full_track_data[plate][pos][track][proc_tuple[1]][proc_tuple[2]][proc_tuple[3]],
                                                        full_track_data[plate][pos][track][proc_tuple[4]][proc_tuple[5]][proc_tuple[6]])

        return res


    def exportTracksHTMLWithoutPanels(self, plate, pos,
                                      full_track_data, lstTracks=None):

        html_dir = os.path.join(self.oSettings.htmlDir, plate, pos)
        if not os.path.isdir(html_dir):
            os.makedirs(html_dir)

        if lstTracks is None:
           lstTracks = sorted(full_track_data[plate][pos].keys())

        if len(lstTracks) == 0:
            print 'no tracks found for ', plate, pos
            return

        # gallery images
        dctRelFilenames = self.getGalleryFilenames(plate, pos)
        if len(dctRelFilenames) == 0:
            print 'no cut outs found'
            return

        # the columns of the html page
        plot_keys = self.oSettings.html_plot_col_title.keys()
        value_keys = self.oSettings.value_extraction.keys()
        print 'plot_keys: ', plot_keys
        print 'value_keys: ', value_keys

        # plots
        dctRelSingleTrackPlots = {}
        for feature in plot_keys:
            dctRelSingleTrackPlots[feature] = self.getPlotFilenames(plate, pos, feature)

        # numerical data
        trackAttributes = self.prepareDataForHTML(full_track_data, plate, pos, lstTracks)

        # columns of HTML page
        columns = ['Track'] +\
                  ['%s' % x for x in self.oSettings.value_extraction.keys()] + \
                  ['Graph: %s' % self.oSettings.html_plot_col_title[x] for x in plot_keys] + \
                  ['Gallery']
        sortable = [True] + [True for x in self.oSettings.value_extraction.keys()] + \
                   [False for x in plot_keys] + \
                   [False]
        missing_graphs = []


        filename = os.path.join(html_dir, 'index_%s_%s.html' % (plate, pos))
        file = open(filename, 'w')
        script_name = os.path.relpath(os.path.join(self.oSettings.htmlResourceDir,
                                                   'sorttable.js'),
                                      html_dir)
        titleString="""
<html>
  <head>
    <title>Single Cell Track Visualization for Lamin Assay: %s %s</title>
    <script type="text/javascript" src="%s"></script>
    <style type="text/css">
    th, td {
      padding: 3px !important;
    }

    /* Sortable tables */
    table.sortable thead {
        background-color:#eee;
        color:#666666;
        font-weight: bold;
        cursor: default;
    }
    </style>
  </head>
  <body>
    <h2>Single Cell Tracks for %s %s (%i / %i tracks) </h2>
    <br clear="all">
    <table align="left" border="0" cellspacing="16" cellpadding="0" class="sortable">
      <thead align="left">
""" % (plate, pos, script_name, plate, pos, len(lstTracks),  len(full_track_data[plate][pos]))

        tempStr = """
      <tr>
     """
        for col, colsort in zip(columns, sortable):
            if not colsort:
                tempStr += """ <th class="sorttable_nosort">%s</th>""" % col
            else:
                tempStr += """ <th>%s</th>""" % col

        tempStr += "</tr>"
        tempStr += """
      </thead>
    <tbody>
"""

        file.write(titleString)
        file.write(tempStr)

        for track in lstTracks:
            includeTrack = True
            for feature in plot_keys:
                # if one graph is not there for the track, discard the track.
                if not track in dctRelSingleTrackPlots[feature]:
                    includeTrack = False
                    break
            if not includeTrack or not track in dctRelFilenames:
                #print 'missing plot or gallery for track %s %s %s ' % (plate, pos, track)
                missing_graphs.append((track, includeTrack, track in dctRelFilenames))
                continue

            strRow = """
    <tr>
      <td align="left" valign="center" nowrap> <font size=3> %s </td>""" % track

            for key in value_keys:
                strRow += """
      <td align="left" valign="center" nowrap> <font size=3> %f </td>""" % trackAttributes[track][key]
            for key in plot_keys:
                strRow += """
      <td align="center"><img src="%s" border="0" height=%i></td>""" % (dctRelSingleTrackPlots[key][track], self.PLOT_HEIGHT)

            strRow += """
      <td align="center"><img src="%s" border="0"></td>""" % dctRelFilenames[track]

            strRow += """
    </tr>
"""
            file.write(strRow)

        endString = """
  </tbody>
  </table>
  </body>
</html>
"""
        file.write(endString)
        file.close()

        # write missing_plots to log
        log_dir = os.path.join(html_dir, 'log')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        filename = os.path.join(log_dir, 'missing_plots_%s_%s.txt' % (plate, pos))
        file = open(filename, 'w')
        file.write('TrackId\tAll Plots present\tGallery present\n')
        for missgraph in missing_graphs:
            file.write('\t'.join([str(x) for x in missgraph]) + '\n')
        file.close()

        return

    def exportTracksHTML(self, plate, pos,
                         full_track_data, lstTracks=None):

        html_dir = os.path.join(self.oSettings.htmlDir, plate, pos)
        if not os.path.isdir(html_dir):
            os.makedirs(html_dir)

        if lstTracks is None:
           lstTracks = sorted(full_track_data[plate][pos].keys())

        if len(lstTracks) == 0:
            print 'no tracks found for ', plate, pos
            return

        # gallery images
        dctRelFilenames = self.getGalleryFilenames(plate, pos)
        if len(dctRelFilenames) == 0:
            print 'no cut outs found'
            return

        # the columns of the html page
        plot_keys = self.oSettings.html_plot_col_title.keys()
        value_keys = self.oSettings.value_extraction.keys()
        upper_panels = self.oSettings.upper_panels
        lower_panels = self.oSettings.lower_panels

        print 'plot_keys: ', plot_keys
        print 'value_keys: ', value_keys

        # plots
        dctRelSingleTrackPlots = {}
        for feature in plot_keys:
            dctRelSingleTrackPlots[feature] = self.getPlotFilenames(plate, pos, feature)
            print 'for feature %s: %i plots found' % (feature, len(dctRelSingleTrackPlots[feature]))

        # panels
        dctTrackPanels = {}
        panels = upper_panels + lower_panels
        for panel in panels:
            dctTrackPanels[panel] = self.getPanelFilenames(plate, pos, panel)
            print 'for panel %s: %i plots found' % (panel, len(dctTrackPanels[panel]))

        # numerical data
        trackAttributes = self.prepareDataForHTML(full_track_data, plate, pos, lstTracks)

        # columns of HTML page
        columns = ['Track'] +\
                  ['%s' % x for x in self.oSettings.value_extraction.keys()] + \
                  ['Graph: %s' % self.oSettings.html_plot_col_title[x] for x in plot_keys] + \
                  ['Gallery']
        sortable = [True] + [True for x in self.oSettings.value_extraction.keys()] + \
                   [False for x in plot_keys] + \
                   [False]
        missing_graphs = []


        filename = os.path.join(html_dir, 'index_%s_%s.html' % (plate, pos))
        file = open(filename, 'w')
        script_name = os.path.relpath(os.path.join(self.oSettings.htmlResourceDir,
                                                   'sorttable.js'),
                                      html_dir)
        titleString="""
<html>
  <head>
    <title>Single Cell Track Visualization for Lamin Assay: %s %s</title>
    <script type="text/javascript" src="%s"></script>
    <style type="text/css">
    th, td {
      padding: 3px !important;
    }

    /* Sortable tables */
    table.sortable thead {
        background-color:#eee;
        color:#666666;
        font-weight: bold;
        cursor: default;
    }
    </style>
  </head>
  <body>
    <h2>Single Cell Tracks for %s %s (%i / %i tracks) </h2>
    <br clear="all">
    <table align="left" border="0" cellspacing="16" cellpadding="0" class="sortable">
      <thead align="left">
""" % (plate, pos, script_name, plate, pos, len(lstTracks),  len(full_track_data[plate][pos]))

        tempStr = """
      <tr>
     """
        for col, colsort in zip(columns, sortable):
            if not colsort:
                tempStr += """ <th class="sorttable_nosort">%s</th>""" % col
            else:
                tempStr += """ <th>%s</th>""" % col

        tempStr += "</tr>"
        tempStr += """
      </thead>
    <tbody>
"""

        file.write(titleString)
        file.write(tempStr)

        for track in lstTracks:
            includeTrack = True
            for feature in plot_keys:
                # if one graph is not there for the track, discard the track.
                if not track in dctRelSingleTrackPlots[feature]:
                    includeTrack = False
                    break

            if not includeTrack or not track in dctRelFilenames:
                missing_graphs.append((track, includeTrack, track in dctRelFilenames))
                continue

            # Track
            strRow = """
    <tr>
      <td align="left" valign="center" nowrap> <font size=3> %s </td>""" % track

            # single numerical values
            for key in value_keys:
                strRow += """
      <td align="left" valign="center" nowrap> <font size=3> %f </td>""" % trackAttributes[track][key]

            # plots
            for key in plot_keys:
                strRow += """
      <td align="center"><img src="%s" border="0" height=%i></td>""" % (dctRelSingleTrackPlots[key][track], self.PLOT_HEIGHT)

            # gallery images with panels
            strRow += """
      <td align="center">
      <table>"""

            # upper panels
            for panel in upper_panels:
                strRow += """
         <tr><td  align="left"><img src="%s" border="0"></td></tr>""" % dctTrackPanels[panel][track]

            # gallery image
            strRow += """
            <tr><td  align="left"><img src="%s" border="0"></td></tr>""" % dctRelFilenames[track]

            # lower panels
            for panel in lower_panels:
                strRow += """
         <tr><td  align="left"><img src="%s" border="0"></td></tr>""" % dctTrackPanels[panel][track]

            strRow += """
      </table>
      </td>"""
          #<td align="center"><img src="%s" border="0"></td>""" % dctRelFilenames[track]

            # end of line
            strRow += """
    </tr>
"""
            file.write(strRow)

        endString = """
  </tbody>
  </table>
  </body>
</html>
"""
        file.write(endString)
        file.close()

        # write missing_plots to log
        log_dir = os.path.join(html_dir, 'log')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        filename = os.path.join(log_dir, 'missing_plots_%s_%s.txt' % (plate, pos))
        file = open(filename, 'w')
        file.write('TrackId\tAll Plots present\tGallery present\n')
        for missgraph in missing_graphs:
            file.write('\t'.join([str(x) for x in missgraph]) + '\n')
        file.close()

        return
