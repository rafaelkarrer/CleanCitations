import sys
if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3")

from tkinter import Frame, Tk, BOTH, Text, Menu, END, RIGHT, Y, StringVar, Label, Scrollbar
from tkinter import filedialog 
import bibtexparser
from difflib import SequenceMatcher
from copy import copy
import threading
import Levenshtein
import time

class LoopingThread(threading.Thread):
    def __init__(self, fcn):
        threading.Thread.__init__(self)
        self.fcn = fcn
        self.loop = True
    def run(self):
        while self.loop:
            self.fcn()
            time.sleep(0.5)
    def stop_loop( self ):
        self.loop = False
        
class BibTexCleanerGUI(Frame):

    def __init__(self, parent):
        Frame.__init__(self, parent)   

        self.parent = parent        
        self.initUI()

    def initUI(self):

        self.parent.title("BibTexCleaner")
        self.pack(fill=BOTH, expand=1)

        menubar = Menu(self.parent)
        self.parent.config(menu=menubar)

        fileMenu = Menu(menubar, tearoff=0)
        fileMenu.add_command(label="Open", command=self.onOpen)
        fileMenu.add_separator()
        fileMenu.add_command( label="Exit", command=self.quit )
        menubar.add_cascade(label="File", menu=fileMenu)        

        # self.stringvar = StringVar()
        # self.stringvar.set('Test')

        # self.label = Label(self.parent, textvariable=self.stringvar)
        # self.label.pack()

        scrollbar = Scrollbar(self)
        scrollbar.pack( side = RIGHT, fill = Y )
        
        self.txt = Text(self, yscrollcommand=scrollbar.set )
        self.txt.pack(fill=BOTH, expand=1)
        
        scrollbar.config( command = self.txt.yview )

        
    def onOpen(self):

        ftypes = [('BibTex files', '*.bib'), ('All files', '*.*')]
        dlg = filedialog.Open(self, filetypes = ftypes)
        fl = dlg.show()

        if fl != '':
            #self.parseBibTex( fl )
            #text = self.readFile(fl)
            #self.txt.insert(END, text)
            self.new_thread = threading.Thread( target=self.parseBibTex, kwargs={'filename':fl} )
            self.new_thread.start()
        
    def readFile(self, filename):

        f = open(filename, "r")
        text = f.read()
        return text
        
    def parseBibTex( self, filename ):
        self.txt.insert(END, '--------------------------------------------------------\r\n' ) 
        self.txt.insert( END, 'Loading file ' + filename + '... ' )
        with open( filename ) as bibtex_file:
            self.txt.insert( END, 'File Loaded.\r\n' )
            self.txt.insert( END, 'Parsing file ' + filename + '... ' )
            bib_database = bibtexparser.load( bibtex_file )        
            self.txt.insert( END, 'File parsed.\r\n' )    
            
        self.txt.insert( END, 'Found ' + str(len(bib_database.entries)) + ' BibTex entries.\r\n' )
        self.txt.insert(END, '--------------------------------------------------------\r\n\r\n' ) 
        self.txt.see( END )
        
        if len(bib_database.entries) == 0:
            print('No bibtex entries found in file!')
            exit()

        attrDict = {'doi':1.0, 'ISSN':1.0, 'ISBN':1.0, 'title':0.9}
        
        dup_dict = dict()
        
        
        for i in range(0,len( attrDict.keys() )):
            self.txt.insert( END, 'Searching for duplicate \'' + attrDict.keys()[i] + '\'s, pthr = ' + str(attrDict[attrDict.keys()[i]]) + '\r\n' )
            self.progressThread = LoopingThread( self.progressBarAdvance )
            self.progressThread.start()
            d = self.attributeMatch( bib_database.entries, attrDict.keys()[i], attrDict[attrDict.keys()[i]] )            # exact match for 'doi'
            self.progressThread.stop_loop()

            dup_dict = dict( dup_dict.items() + d.items() )

        # collect duplicates in separate database file, clean original from duplicates
        bib_database_dup = copy( bib_database )
        bib_database_cln = copy( bib_database )

        bib_database_dup.entries = [ bib_database.entries[i] for i in dup_dict.keys() ]
        bib_database_cln.entries = [ bib_database.entries[i] for i in range(0,len(bib_database.entries)) if i not in dup_dict.keys() ]
        
        self.txt.insert( END, '\r\nFinished analyzing!\r\n' )
        
        self.txt.insert(END, '--------------------------------------------------------\r\n' ) 
        self.txt.insert(END, 'Found ' + str( len(bib_database_dup.entries) ) + ' DUPLICATE entries. Saving to ' + filename[0:-4] + '_duplicates.bib.' + '\r\n' ) 
        self.txt.insert(END, '--------------------------------------------------------\r\n' )
        
        filename_dup = filename[0:-4] + '_duplicates.bib'
        with open( filename_dup, 'w') as bibtex_file:
            bibtexparser.dump(bib_database_dup, bibtex_file)

        self.txt.insert(END, '--------------------------------------------------------\r\n' ) 
        self.txt.insert(END, 'Found ' + str( len(bib_database_cln.entries) ) + ' UNIQUE entries. Saving to ' + filename[0:-4] + '_cleaned.bib.' + '\r\n' ) 
        self.txt.insert(END, '--------------------------------------------------------\r\n' ) 
        
        self.txt.see( END )
        
        filename_cln = filename[0:-4] + '_cleaned.bib'
        with open( filename_cln, 'w') as bibtex_file:
            bibtexparser.dump(bib_database_cln, bibtex_file)

            
    def attributeMatch( self, bibitems, attr, thr=1.0 ):
        dup_list = dict()
        for i in range( 0, len( bibitems ) ):
            try:
                cur_val = bibitems[i][attr]
            except KeyError:
                #self.txt.insert(END, 'No ' + '\'' + attr + '\'' + ' attribute found for ' + bibitems[i]['author'] + ' ' + bibitems[i]['year'] +'\r\n' ) 
                continue
                
            for j in range( i+1, len( bibitems ) ):
                try:
                    #ratio = self.probSequenceMatch( cur_val, bibitems[j][attr] )
                    ratio = self.probStringSimilarity( cur_val.lower(), bibitems[j][attr].lower() )
                    #ratio = cur_val == bibitems[j][attr]
                    #ratio = 1.0
                    if ratio >= thr:
                        dup_list[j] = ratio
                        if ratio == 1.0:
                            pass
                            #self.txt.insert(END, 'Exact ' + '\'' + attr + '\'' + ' match for ' + bibitems[i]['author'] + ', ' + bibitems[i]['year'] + ', index='+str(j) + '\r\n' ) 
                            #print 'Exact', '\'' + attr + '\'', 'match for', bibitems[i]['author'], bibitems[i]['year'], 'index='+str(j)
                        else:
                            pass
                            #self.txt.insert(END, 'Soft ' + '\'' + attr + '\'' + ' match for ' + bibitems[i]['author'] + ', ' + bibitems[i]['year'] + ', index='+str(j) + ', prob='+str(ratio) + '\r\n' ) 
                            #self.txt.insert(END, cur_val+'\r\n' )
                            #self.txt.insert(END, 'VS.\r\n' )
                            #self.txt.insert(END, bibitems[j][attr]+'\r\n' )

                            #print 'Soft', '\'' + attr + '\'', 'match for', bibitems[i]['author'], bibitems[i]['year'], 'index='+str(j), 'prob='+str(ratio)
                        #self.txt.insert(END, 'x' ); #self.txt.see( END )
                    else:
                        pass
                        #self.txt.insert(END, '.' ); #self.txt.see( END )
                except KeyError:
                    pass
                    #print 'No', '\'' + attr + '\'', 'attribute found for', bibitems[i]['author'], bibitems[i]['year']
        self.txt.insert(END, '\r\n' )
        return dup_list

    def progressBarAdvance( self ):
        self.txt.insert(END, '.' );
        self.txt.see( END )
        time.sleep( 0.5 )
        
    def probStringSimilarity( self, s1, s2 ):
        return Levenshtein.ratio( s1, s2 )
        
    def probSequenceMatch(self, s1, s2):
        return SequenceMatcher(None, s1, s2).ratio()
        
def main():

    root = Tk()
    ex = BibTexCleanerGUI(root)
    root.geometry("1600x250+100+300")
    root.mainloop()  


if __name__ == '__main__':
    main()  
