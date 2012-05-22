import numpy
import csv
import pylab
import re
import os
import cPickle as pickle
import colorbrewer
from itertools import cycle
from cecog.util.color import rgb_to_hex
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib as mpl
#mpl.rcParams["axes.facecolor"] = 'k'
#mpl.rcParams["axes.edgecolor"] = 'w'
#mpl.rcParams["axes.labelcolor"] = 'w'
mpl.rcParams["figure.facecolor"] = 'w'



def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

class EventPlotterPdf(object):
    def __init__(self, figsize):
        self.figure = pylab.figure(figsize)
        self.axes = self.figure.add_subplot(111)
        self._pdf_handle = None
        
    def clear(self):
        self.figure.clf()
    
    def open(self, filename):
        self._pdf_handle = PdfPages(filename)
    
    def close(self):
        if self._pdf_handle is not None:
            self._pdf_handle.close()
    
    def save(self):
        self.figure.savefig(self._pdf_handle, format='pdf')
    
    def __del__(self):
        self.close()
              
class GalleryDecorationPlotter(EventPlotterPdf):
    def add_gallery_deco(self):
        
        
        


class IBBAnalysis(object):
    REJECTION = enum('OK', "BY_SIGNAL", "BY_SPLIT", "BY_IBB_ONSET", "BY_NEBD_ONSET")
    
    IBB_RATIO_SIGNAL_THRESHOLD = 1.0
    IBB_RANGE_SIGNAL_THRESHOLD = 0.5
    IBB_ZERO_CORRECTION = 0.025
    
    IBB_ONSET_FACTOR_THRESHOLD   = 1.2
    NEBD_ONSET_FACTOR_THRESHOLD  = 1.2
    
    SINGLE_PLOT = False
    
    PLOT_IDS =    ['nebd_to_sep_time', 'sep_to__ibb_time', 'prophase_to_nebd']
    PLOT_LABELS = ['nebd_to_sep_time', 'sep_to__ibb_time', 'prophase_to_nebd']
    
    def __init__(self, path_in, path_out, plate_name, mapping_file, class_colors):
        self.plate_name = plate_name
        self.path_in = path_in
        self.path_out = path_out
        self.mapping_file = mapping_file
        self.class_colors = class_colors
        self._plotter = {}
        self._pylab_fig = None
        
    
    def _readScreen(self):
        self.plate = Plate.load(self.path_in, self.plate_name)
        #self.plate = Plate(self.plate_name, self.path_in, self.mapping_file)
    
    def run(self):
        try:
            self._readScreen()
            grouped_positions = self.plate.get_events(2)
            for group_name in grouped_positions:
                self._plotter[group_name] = GalleryDecorationPlotter()
                self._plotter[group_name].open(os.path.join(self.path_out, 'ibb__PL%s__%s__single_plots.pdf' % (self.plate_name, group_name)))
            self._run(self.plate_name, grouped_positions)
        finally:
            for pl in self._plotter.values():
                pl.close()  
                 
    def _run(self, plate_id, grouped_positions):
        result = {}
        for group_name, pos_list in grouped_positions.items():
            result[group_name] = {}
            result[group_name]['positions'] = []
            
            result[group_name]['nebd_to_sep_time'] = []
            result[group_name]['sep_to__ibb_time'] = []
            result[group_name]['prophase_to_nebd'] = []
            result[group_name]['valid'] = [0,0,0,0,0] 
            
            for pos in pos_list:
                result[group_name]['positions'].append(pos)
                for event_idx, (event_id, event_dicts) in enumerate(sorted(pos.items())):
                    print event_idx, event_id
                    h2b = event_dicts['Primary']['primary']
                    ibb_inside = event_dicts['Secondary']['inside']
                    ibb_outside = event_dicts['Secondary']['outside']
                    
                    ins = ibb_inside['feature__n2_avg'] + IBBAnalysis.IBB_ZERO_CORRECTION
                    out = ibb_outside['feature__n2_avg'] + IBBAnalysis.IBB_ZERO_CORRECTION
                    ibb_ratio = ins / out
                    
                    rejection_code, ibb_result = self._analyze_ibb(h2b, ibb_ratio)
                    result[group_name]['valid'][rejection_code] += 1
                    
                    time = h2b['timestamp'] 
                    time = time - time[0]
                    
                    if rejection_code == IBBAnalysis.REJECTION.OK:
                        separation_frame, ibb_onset_frame, nebd_onset_frame, prophase_last_frame = ibb_result
                        
                        result[group_name]['nebd_to_sep_time'].append(time[separation_frame] - time[nebd_onset_frame])
                        result[group_name]['sep_to__ibb_time'].append(time[ibb_onset_frame] - time[separation_frame])
                        result[group_name]['prophase_to_nebd'].append(time[nebd_onset_frame] - time[prophase_last_frame])
                        
                        if IBBAnalysis.SINGLE_PLOT:
                            self._plot_single_event(group_name, ibb_ratio, h2b, 
                                                    separation_frame, 
                                                    ibb_onset_frame, 
                                                    nebd_onset_frame, 
                                                    prophase_last_frame,
                                                    event_id, pos.position)
                                                   
            
        self._plot(result, "nebd_to_sep_time")                        
                
    
    def _analyze_ibb(self, h2b, ibb_ratio):
        rejection_code, separation_frame = self._find_separation_event(h2b)
        if rejection_code != IBBAnalysis.REJECTION.OK:
            return rejection_code, None
        

        rejection_code = self._check_signal(ibb_ratio)
        if rejection_code != IBBAnalysis.REJECTION.OK:
            return rejection_code, None
        
        rejection_code, ibb_onset_frame = self._find_ibb_onset_event(ibb_ratio, separation_frame)
        if rejection_code != IBBAnalysis.REJECTION.OK:
            return rejection_code, None

        rejection_code, nebd_onset_frame = self._find_nebd_onset_event(ibb_ratio, separation_frame)
        if rejection_code != IBBAnalysis.REJECTION.OK:
            return rejection_code, None
        
        rejection_code, prophase_last_frame = self._find_prophase_last_frame(h2b, nebd_onset_frame)
        if rejection_code != IBBAnalysis.REJECTION.OK:
            return rejection_code, None
        
        return IBBAnalysis.REJECTION.OK, (separation_frame, ibb_onset_frame, nebd_onset_frame, prophase_last_frame)
              
              
    def _find_prophase_last_frame(self, h2b, nebd_onset_frame):
        for x in reversed(range(nebd_onset_frame+2)):
            label = h2b['class__label'][x]
            if label == 1:
                return IBBAnalysis.REJECTION.OK, x
        return IBBAnalysis.REJECTION.BY_NEBD_ONSET, None
    
    def _get_relative_time(self, h2b, frame_idx):
        return h2b['timestamp'][frame_idx] - h2b['timestamp'][0]
        
    def _find_class_timing(self, h2b):
        pass
            
        
    def _find_separation_event(self, h2b):
        # separation event found by isplit entry
        separation_frame = h2b['issplit'].nonzero()[0]
        if len(separation_frame) != 0:
            return IBBAnalysis.REJECTION.OK, separation_frame[0]
        
        # try first early ana phase
        separation_frame = h2b['class__label'].nonzero()[0]
        if len(separation_frame) == 1:
            return IBBAnalysis.REJECTION.OK, separation_frame[0]
        
        # try meta -> late ana transition
        transition = ''.join(map(str, h2b['class__label'])).find('46') + 1
        if transition > 1:
            return IBBAnalysis.REJECTION.OK, transition
        
        return IBBAnalysis.REJECTION.BY_SPLIT, None
    
    def _check_signal(self, ibb_ratio):
        if ibb_ratio.mean() < IBBAnalysis.IBB_RATIO_SIGNAL_THRESHOLD or \
           (ibb_ratio.max() - ibb_ratio.min()) < IBBAnalysis.IBB_RANGE_SIGNAL_THRESHOLD:
            return IBBAnalysis.REJECTION.BY_SIGNAL
        
        return IBBAnalysis.REJECTION.OK 
            
    
    def _find_ibb_onset_event(self, ibb_ratio, separation_frame):
        ibb_onset_frame = separation_frame - 1
        while True:
            if ibb_ratio[ibb_onset_frame] >= ibb_ratio[separation_frame] * IBBAnalysis.IBB_ONSET_FACTOR_THRESHOLD:
                ibb_onset_frame -= 1
                break
            elif ibb_onset_frame >= len(ibb_ratio)-2:
                ibb_onset_frame = None
                break
            ibb_onset_frame += 1
        
        if ibb_onset_frame is None:
            return IBBAnalysis.REJECTION.BY_IBB_ONSET, None
        
        return IBBAnalysis.REJECTION.OK, ibb_onset_frame
        
    
    def _find_nebd_onset_event(self, ibb_ratio, separation_frame):
        nebd_onset_frame = ibb_ratio.argmin() + 1
        
        if nebd_onset_frame > separation_frame:
            nebd_onset_frame = separation_frame
    
        while True:
            nebd_onset_frame -= 1
            if ibb_ratio[nebd_onset_frame] / ibb_ratio[nebd_onset_frame+1] >= IBBAnalysis.NEBD_ONSET_FACTOR_THRESHOLD:
                break
            elif nebd_onset_frame <= 0:
                nebd_onset_frame = None
                break
    
        if nebd_onset_frame is None:
            return IBBAnalysis.REJECTION.BY_NEBD_ONSET, None
        
        return IBBAnalysis.REJECTION.OK, nebd_onset_frame
        
    def _plot_single_event(self, group_name, ratio, h2b, 
                           separation_frame, 
                           ibb_onset_frame, 
                           nebd_onset_frame,
                           prophase_last_frame, 
                           event_id, pos_name):
        
        if self._pylab_fig is None:
            self._pylab_fig = pylab.figure(figsize=(8, 4))
        fig = self._pylab_fig
        pylab.clf()
        
        time = h2b['timestamp'] 
        time = time - time[0]
        time /= 60.0
        
        pylab.plot(time, ratio, 'k.-', label="Ibb ratio")
        pylab.plot([time[separation_frame], time[separation_frame]], [ratio.min(), ratio.max()], 'r', label="Sep")
        pylab.plot([time[ibb_onset_frame], time[ibb_onset_frame]], [ratio.min(), ratio.max()], 'g', label="Ibb onset")
        pylab.plot([time[nebd_onset_frame], time[nebd_onset_frame]], [ratio.min(), ratio.max()], 'b', label="Nebd")
        pylab.plot([time[prophase_last_frame], time[prophase_last_frame]], [ratio.min(), ratio.max()], 'y', label="Pro")
        
        
        pylab.ylim(ratio.min(),ratio.max())
        pylab.xlim(0, time[-1])
        pylab.title("%s - %s" % (group_name, event_id))
        pylab.ylabel("IBB ratio")
        pylab.xlabel("Time [min]")
#        pylab.text(time[separation_frame]+0.5, ratio.max(), "Sep", verticalalignment='top', color='r')
#        pylab.text(time[ibb_onset_frame]+0.5, ratio.max(), "Ibb", verticalalignment='top', color='g')
#        pylab.text(time[nebd_onset_frame]+0.5, ratio.max(), "Nebd", verticalalignment='top', color='b')
        pylab.legend(loc="lower right", prop={'size':6})
        pylab.grid('on')
        
        class_labels = h2b['class__label']
        
        for t in xrange(len(time)-1):
#            pylab.axvspan(time[t], time[t+1], ratio.min(), (ratio.max()-ratio.min())/20.0, color=self.class_colors[class_labels[t]])
#            pylab.axvspan(time[t], time[t+1], ratio.min(), (ratio.max()-ratio.min())/20.0, color=self.class_colors[class_labels[t]])
            pylab.gca().add_patch(pylab.Rectangle((time[t], ratio.min()),
                                                  time[t+1]-time[t],
                                                  (ratio.max()-ratio.min())/20.0, 
                                                  fill=True, 
                                                  color=self.class_colors[class_labels[t]]))
            
            
        #fig.savefig(os.path.join(self.path_out, '___ibb_plot_%s_%s.png' % (pos_name, event_id)))
        fig.savefig(self._multi_page_pdf_handle[group_name], format='pdf')
        
    def _plot(self, result, id, color_sort_by="group"):
        data = []
        names = []
        colors = []
        base_colors = cycle(colorbrewer.Set3[8])
        def mycmp(x, y):
            return cmp(result[x]['positions'][0].__getattribute__(color_sort_by).lower(), 
                       result[y]['positions'][0].__getattribute__(color_sort_by).lower())
        
        last_id = 'hamster'
        for group_name in sorted(result, cmp=mycmp):
            new_id = result[group_name]['positions'][0].__getattribute__(color_sort_by)
            print new_id
            
            data.append(numpy.array(result[group_name][id])/60.0)
            
            if isinstance(group_name, int):
                names.append("%s (%04d)" % (new_id, group_name))
            else:
                names.append("%s (%s)" % (new_id, group_name))

            if last_id != new_id:
                color = base_colors.next()
                last_id = result[group_name]['positions'][0].__getattribute__(color_sort_by)
            colors.append(color)
                

        
        self._boxplot(data, names, colors)
            
            
            
        
    def _boxplot(self, data_list, names, colors):
        fig = pylab.figure(figsize=(10,6))
        fig.canvas.set_window_title('Ibb Analysis')
        ax1 = fig.add_subplot(111)
        bp = pylab.boxplot(data_list, patch_artist=True)
        pylab.setp(bp['boxes'], color='black')
        pylab.setp(bp['whiskers'], color='black')
        pylab.setp(bp['fliers'], markerfacecolor='w', marker='o', markeredgecolor='k')
        for b, c in zip(bp['boxes'], colors):
            pylab.setp(b, facecolor=rgb_to_hex(*c))
        
        xtickNames = pylab.setp(ax1, xticklabels=names)
        pylab.setp(xtickNames, rotation=45, fontsize=12)
        pylab.ylim(0,100)
        
        pylab.show()
        
        
        
        
        
    
    
class Position(dict):
    def __init__(self, plate,
                        position,
                        well,
                        site,
                        row,
                        column,
                        gene_symbol,
                        oligoid,
                        group):
        dict.__init__(self)
        self.plate = plate
        self.position = position
        self.well = well
        self.site = site
        self.row = row
        self.column = column
        self.gene_symbol = gene_symbol
        self.oligoid = oligoid
        self.group = group  
        
    def __str__(self):
        return "p %s, o %s, g %s, g %s" % ( self.position, self.oligoid, self.gene_symbol, self.group)
    
    def __repr__(self):
        return "p %s, o %s, g %s, g %s" % ( self.position, self.oligoid, self.gene_symbol, self.group)
    
class Plate(object):
    GROUP_BY_POS = 1
    GROUP_BY_OLIGO = 2
    GROUP_BY_GENE = 3
    GROUP_BY_GROUP = 4
    
    POSITION_REGEXP = re.compile(r"^[A-Z]\d{1,5}_\d{1,5}$|^\d{1,6}$")
    EVENT_REGEXP = re.compile(r"features__P(?P<pos>\d+|[A-Z]\d+_\d+)__T(?P<time>\d+)"
                               "__O(?P<obj>\d+)__B(?P<branch>\d+)__C(?P<channel>.+?)__R(?P<region>.*)\.txt")
    def __init__(self, plate_id, path_in, mapping_file):
        self.plate_id = plate_id
        self.path_in = path_in
        self.mapping_file = mapping_file
        self._positions = {}
        self.readEvents()
        
    def __str__(self):
        res = ""
        for pos in self._positions:
            res += "%s with %d events\n" % (pos, len(self._positions[pos]))
        return res
    
    def __repr_(self):
        res = ""
        for pos in self._positions:
            res += "%s with %d events\n" % (pos, len(self._positions[pos]))
        return res
    
    def readEvents(self):
        self.mapping = self._readMappingFile()
        self.pos_list = self._get_positions_dirs()
        
        for pos_idx, pos_name in enumerate(self.mapping['position']):
            if isinstance(pos_name, int):
                pos_name = '%04d' % pos_name
                    
            if pos_name not in self.pos_list:
#                raise RuntimeError("Position from Mapping file %s not found in in path %s" % (pos_name, self.path_in))
                print "Position from Mapping file %s not found in in path %s" % (pos_name, self.path_in)
                continue
            
            event_path = os.path.join(self.path_in, pos_name, 'statistics' , 'events')
            if not os.path.exists(event_path):
                raise RuntimeError("For position %s no event path found %s" % (pos_name, event_path))
            
            event_file_list = sorted(os.listdir(event_path))
            if len(event_file_list) == 0:
                print "WARNING: No events found for position", pos_name
                continue
            
            print "Reading Events for position '%s' (%d files)" % (pos_name, len(event_file_list))
            for event_file in event_file_list:
                res = self.EVENT_REGEXP.search(event_file)
                if res is None:
                    print "WARNING: Could not parse event file name '%s' for position %s" % (event_file, pos_name) 
                    continue
                
                res = res.groupdict()
                if pos_name != res['pos']:
                    raise RuntimeError("Event file %s has different pos identifier than %s" % (event_file, pos_name))
            
                channel = res["channel"]
                region = res["region"]
                branch = int(res["branch"])
                time = int(res["time"])
                obj = int(res["obj"])
                
                if branch == 1:
                    
                    if pos_name not in self._positions.keys():
                        self._positions[pos_name] = Position(plate=self.plate_id,
                                                            position=self.mapping[pos_idx]['position'],
                                                            well=self.mapping[pos_idx]['well'],
                                                            site=self.mapping[pos_idx]['site'],
                                                            row=self.mapping[pos_idx]['row'],
                                                            column=self.mapping[pos_idx]['column'],
                                                            gene_symbol=self.mapping[pos_idx]['gene_symbol'],
                                                            oligoid=self.mapping[pos_idx]['oligoid'],
                                                            group=self.mapping[pos_idx]['group'], 
                                                            )
                        
                    event_id = 'T%04d_O%04d_B%d' % (time, obj, branch)
                    if event_id not in self._positions[pos_name]:
                        self._positions[pos_name][event_id] = {} 
                    
                    if channel not in self._positions[pos_name][event_id]:
                        self._positions[pos_name][event_id][channel] = {}
                        
                    filename = os.path.join(event_path, event_file)
                    self._positions[pos_name][event_id][channel][region] = numpy.recfromcsv(filename, delimiter='\t') 
                    
                           
    def _readMappingFile(self):
        if os.path.exists(self.mapping_file):
            mapping = numpy.recfromcsv(self.mapping_file, delimiter='\t')
        else:
            raise RuntimeError("Mapping file does not exist %s" % self.mapping_file)
        
        if len(mapping) == 0:
            raise RuntimeError("Mapping file is empty %s" % self.mapping_file)
        
        return mapping
        
        
    def _get_positions_dirs(self):
        pos_list = []
        for pos_candidate in sorted(os.listdir(self.path_in)):
            if self.POSITION_REGEXP.search(pos_candidate) is not None:
                pos_list.append(pos_candidate)
                
        if len(pos_list) == 0:
            raise RuntimeError("No positions folder found for path %s" % self.path_in)
            
        return pos_list
    
    def get_events(self, group_by=1):
        res = {}
        for pos in self._positions.values():
            if group_by == self.GROUP_BY_POS:
                group_key = pos.position
            elif group_by == self.GROUP_BY_OLIGO:
                group_key = pos.oligoid
            elif group_by == self.GROUP_BY_GENE:
                group_key = pos.gene_symbol
            elif group_by == self.GROUP_BY_GROUP:
                group_key = pos.group
            else:
                raise AttributeError("group_by argument not understood %r" % group_by)
        
            if pos.position not in res:
                res[group_key] = []
            res[group_key].append(pos)
                
        return res
    
    def save(self):
        f = open(os.path.join(self.path_in, self.plate_id + ".pkl"), 'w')
        pickle.dump(self, f)
        f.close()
        
    
    @staticmethod
    def load(path_in, plate_id):
        f = open(os.path.join(path_in, plate_id + ".pkl"), 'r')
        plate = pickle.load(f)
        f.close()
        return plate
               
def test_plate():
    Plate("plate_name", r"C:\Users\sommerc\data\cecog\Analysis\H2b_aTub_MD20x_exp911_2_channels_zip\analyzed", 
                            r"C:\Users\sommerc\data\cecog\Mappings\plate_name.txt")
    print 'done'
    
def test_plate_2():
    a = Plate("plate_name", r"Y:\amalie\Analysis\001872_2_longer\analyzed", 
                            r"Y:\amalie\Mappings\001872\001872.txt")
    
    a.save()
    print 'done'
    
    
def test_ibb():
    class_colors = {1: '#00ff00',
                    2: '#fff643',
                    3: '#ff8000',
                    4: '#d28dce',
                    5: '#8931ea',
                    6: '#5871f1',
                    7: '#94b22d',
                    8: '#FF0000',
                    9: '#ff00ff',}

    ibb = IBBAnalysis("Y:/amalie/Analysis/001872_2_longer/analyzed", 
                      "Y:/amalie/Analysis/001872_2_longer", 
                      'plate_name', 
                      r"C:\Users\sommerc\data\cecog\Mappings\plate_name.txt", 
                      class_colors)
    
    ibb.run()
    
if __name__ == "__main__":
    test_ibb()
        