#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013, Colin O'Flynn <coflynn@newae.com>
# All rights reserved.
#
# Find this and more at newae.com - this file is part of the chipwhisperer
# project, http://www.assembla.com/spaces/chipwhisperer
#
#    This file is part of chipwhisperer.
#
#    chipwhisperer is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    chipwhisperer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with chipwhisperer.  If not, see <http://www.gnu.org/licenses/>.
#=================================================


import sys

try:
    from PySide.QtCore import *
    from PySide.QtGui import *
except ImportError:
    print "ERROR: PySide is required for this program"
    sys.exit()
    
from datetime import datetime
import random
import os.path
import shlex
from subprocess import Popen, PIPE
sys.path.append('../common')
sys.path.append('../../openadc/controlsw/python/common')
imagePath = '../common/images/'


from ExtendedParameter import ExtendedParameter

try:
    import writer_dpav3
except ImportError:
    writer_dpav3 = None
    writer_dpav3_str = sys.exc_info()

try:
    import pyqtgraph as pg
    import pyqtgraph.multiprocess as mp
    import pyqtgraph.parametertree.parameterTypes as pTypes
    from pyqtgraph.parametertree import Parameter, ParameterTree, ParameterItem, registerParameterType
    #print pg.systemInfo()
    
except ImportError:
    print "ERROR: PyQtGraph is required for this program"
    sys.exit()

try:
    from Crypto.Cipher import AES
except ImportError:
    AES = None    

from scopes.OpenADC import OpenADCInterface as OpenADCInterface

try:
    import targets.SimpleSerial as target_SimpleSerial
except ImportError:
    target_SimpleSerial = None
    target_SimpleSerial_str = sys.exc_info()
    
try:
    import targets.SmartCard as target_SmartCard
except ImportError:
    target_SmartCard = None
    target_SmartCard_str = sys.exc_info()
    
try:
    import targets.SASEBOGII as target_SASEBOGII
except ImportError:
    target_SASEBOGII = None
    target_SASEBOGII_str = sys.exc_info()
    
try:
    import targets.SAKURAG as target_SAKURAG
except ImportError:
    target_SAKURAG = None
    target_SAKURAG_str = sys.exc_info()

from MainChip import MainChip
from ProjectFormat import ProjectFormat
from traces.TraceContainerNative import TraceContainerNative
from traces.TraceContainerDPAv3 import TraceContainerDPAv3

class acquisitionController(QObject):
    traceDone = Signal(int, list, int)
    captureDone = Signal(bool)
    
    def __init__(self, scope, target, writer, fixedPlain=False, updateData=None, textInLabel=None, textOutLabel=None, textExpectedLabel=None):
        super(acquisitionController, self).__init__()

        self.target = target
        self.scope = scope
        self.writer = writer
        self.running = False
        self.fixedPlainText = fixedPlain
        self.maxtraces = 1
        self.updateData = updateData
        self.textInLabel = textInLabel
        self.textOutLabel = textOutLabel
        self.textExpectedLabel = textExpectedLabel

        self.textin = bytearray(16)
        for i in range(0,16):
            self.textin[i] = i #random.randint(0, 255)       

    def TargetDoTrace(self, plaintext, key=None):
        if self.target is None:
            return
           
        self.target.loadInput(plaintext)
        self.target.go()
        
        while self.target.isDone() == False:
            continue

        #print "DEBUG: Target go()"

        resp = self.target.readOutput()
        #print "DEBUG: Target readOutput()"

        #print "pt:",
        #for i in plaintext:
        #    print " %02X"%i,
        #print ""

        #print "sc:",
        #for i in resp:
        #    print " %02X"%i,
        #print ""

        return resp

    def newPlain(self, textIn=None):     
          
        if textIn:
            self.textin = textIn
        else:
            if not self.fixedPlainText:       
                self.textin = bytearray(16)
                for i in range(0,16):
                    self.textin[i] = random.randint(0, 255)
                    #self.textin[i] = i
        #Do AES if setup
        if AES and (self.textExpectedLabel != None):
            if self.key == None:
                self.textExpectedLabel.setText("")
            else:
                cipher = AES.new(str(self.key), AES.MODE_ECB)
                ct = cipher.encrypt(str(self.textin))
                if self.textExpectedLabel != None:
                    ct = bytearray(ct)
                    self.textExpectedLabel.setText("%02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X"%(ct[0],ct[1],ct[2],ct[3],ct[4],ct[5],ct[6],ct[7],ct[8],ct[9],ct[10],ct[11],ct[12],ct[13],ct[14],ct[15]))


    def doSingleReading(self, update=True, N=None, key=None):
       
        self.key = key
        self.newPlain()

        #self.target.init()

        #self.target.read(0xFFFC)
        #self.textin = [0x45, 0xE7 ,0xF9 ,0x71 ,0x0F ,0xFF ,0xB4 ,0x23 ,0xD0 ,0x98 ,0x60 ,0xF3 ,0x94 ,0xBC ,0x51 ,0x10]
        #self.key = range(0,16)

        ## Start target now
        if self.textInLabel != None:
            self.textInLabel.setText("%02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X"%(self.textin[0],self.textin[1],self.textin[2],self.textin[3],self.textin[4],self.textin[5],self.textin[6],self.textin[7],self.textin[8],self.textin[9],self.textin[10],self.textin[11],self.textin[12],self.textin[13],self.textin[14],self.textin[15]))

        #Set mode
        if self.target is not None:
            self.target.setModeEncrypt()
            self.target.loadEncryptionKey(self.key)  
        
        self.scope.arm()

        
        if self.target is not None:            
            #Load input, start encryption, get output
            self.textout = self.TargetDoTrace(self.textin, key)

            if self.textout is not None:
                if len(self.textout) >= 16:    
                    self.textOutLabel.setText("%02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X"%(self.textout[0],self.textout[1],self.textout[2],self.textout[3],self.textout[4],self.textout[5],self.textout[6],self.textout[7],self.textout[8],self.textout[9],self.textout[10],self.textout[11],self.textout[12],self.textout[13],self.textout[14],self.textout[15]))

        #Get ADC reading
        try:
            if self.scope.capture(update, N) == True:
                print "Timeout"
                return False       
        except IOError,e:
            print "IOError: %s"%str(e)
            return False
        
        return True

    def setMaxtraces(self, maxtraces):
        self.maxtraces = maxtraces

    def doReadings(self, addToList=None, key=None):
        self.running = True
        
        self.key = key
        
        if self.writer is not None:
            self.writer.prepareDisk()
            self.writer.setKnownKey(self.key)

        nt = 0

        while (nt < self.maxtraces) and self.running:
            if self.doSingleReading(True, None, key=self.key) == True:
                if self.writer is not None:
                    self.writer.addTrace(self.scope.datapoints, self.textin, self.textout, self.key)            
    
                nt = nt + 1
                self.traceDone.emit(nt, self.scope.datapoints, self.scope.offset)
            QCoreApplication.processEvents()
            

        if self.writer is not None:
            self.writer.closeAll()
        
        if addToList is not None:
            if self.writer is not None:
                addToList.append(self.writer)
        
        self.captureDone.emit(self.running)
        
        self.running = False      

class TargetInterface(QObject):
    """This is a standard target interface, which controls various supported lower-level hardware interfaces"""
    paramListUpdated = Signal(list)
    
    def __init__(self, parent=None, log=None,showScriptParameter=None):
        super(TargetInterface, self).__init__(parent)
        valid_targets = {"None":None}
        self.driver = None
        self.log=log
        self.showScriptParameter = showScriptParameter
                
        if target_SimpleSerial is not None:
            valid_targets["Simple Serial"] = target_SimpleSerial.SimpleSerial(self.log, showScriptParameter=showScriptParameter)
            
        if target_SmartCard is not None:
            valid_targets["Smart Card"] = target_SmartCard.SmartCard(showScriptParameter=showScriptParameter)
            
        if target_SASEBOGII is not None:
            valid_targets["SASEBO GII"] = target_SASEBOGII.SaseboGII(self.log, showScriptParameter=showScriptParameter)
            
        if target_SAKURAG is not None:
            valid_targets["SAKURA G"] = target_SAKURAG.SakuraG(self.log, showScriptParameter=showScriptParameter)
        
        self.toplevel_param = {'name':'Target Module', 'type':'list', 'values':valid_targets, 'value':valid_targets["None"], 'set':self.setDriver}     

    #def paramTreeChanged(self, param, changes):
    #    if self.showScriptParameter is not None:
    #        self.showScriptParameter(param, changes, self.params)

    def setOpenADC(self, oadc):
        '''Declares OpenADC Instance in use. Only for openadc-integrated targets'''
        self.oadc = oadc.scope.sc
        self.driver.setOpenADC(self.oadc)
        
    def con(self):
        if self.driver is not None:
            self.driver.con()
        
    def dis(self):
        if self.driver is not None:
            self.driver.dis()

    def setDriver(self, driver):
        self.driver = driver
        try:
            self.driver.setOpenADC(self.oadc)
        except:
            pass        
        
        if self.driver is None:
            self.paramListUpdated.emit(None)
        else:
            self.driver.paramListUpdated.connect(self.paramListUpdated.emit)
            self.paramListUpdated.emit(self.driver.paramList())
            
    def paramList(self):
        if self.driver is None:
            return [None]
        else:
            return self.driver.paramList()

class FWLoaderConfig(QDialog):   
    def __init__(self, parent=None, console=None):
        super(FWLoaderConfig, self).__init__(parent)
        
        self.console = console
        
        self.setWindowTitle("ChipWhisperer Firmware Loader Configuration")
        
        layout = QVBoxLayout()
        
        layoutFWLoader = QHBoxLayout()
        self.fwLocation = QLineEdit()
        fwButton = QPushButton("Find")
        fwButton.clicked.connect(self.findFWLoader)
        layoutFWLoader.addWidget(QLabel("FWLoader Location"))
        layoutFWLoader.addWidget(self.fwLocation)
        layoutFWLoader.addWidget(fwButton)        
        layout.addLayout(layoutFWLoader) 
 
        layoutBit = QHBoxLayout()
        self.bitLocation = QLineEdit()
        bitButton = QPushButton("Find")
        bitButton.clicked.connect(self.findBitstream)
        layoutBit.addWidget(QLabel("FPGA Bitstream Location"))
        layoutBit.addWidget(self.bitLocation)
        layoutBit.addWidget(bitButton)        
        layout.addLayout(layoutBit) 
        
        layoutFW = QHBoxLayout()
        self.firmwareLocation = QLineEdit()
        firmwareButton = QPushButton("Find")
        firmwareButton.clicked.connect(self.findFirmware)
        layoutFW.addWidget(QLabel("Firmware Location"))
        layoutFW.addWidget(self.firmwareLocation)
        layoutFW.addWidget(firmwareButton)        
        layout.addLayout(layoutFW)      

        # Set dialog layout
        self.setLayout(layout)
        
        settings = QSettings()
        self.fwLocation.setText(settings.value("fwloader-location"))
        self.bitLocation.setText(settings.value("bitstream-location"))
        self.firmwareLocation.setText(settings.value("firmware-location"))
       
    def findFWLoader(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Find FWLoader','.','FWLoader.jar')        
        if fname:
            self.fwLocation.setText(fname)
            QSettings().setValue("fwloader-location", fname)
            
    def findBitstream(self):   
        fname, _ = QFileDialog.getOpenFileName(self, 'Find Bitstream','.','*.bit')        
        if fname:
            self.bitLocation.setText(fname)
            QSettings().setValue("bitstream-location", fname)
            
    def findFirmware(self):   
        fname, _ = QFileDialog.getOpenFileName(self, 'Find Firmware','.','*.ihx')        
        if fname:
            print fname
            self.firmwareLocation.setText(fname)
            QSettings().setValue("firmware-location", fname)
           
    def getStatus(self):
        """Get the output of the FWLoader command with the -i (info) option"""
        #Check Status
        cmd = "java -cp %s FWLoader -c -i"%(self.fwLocation.text())
        process = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        process.wait()
        
        if "devices" in stderr:
            if self.console:
                self.console.append(stderr)
        return stdout
            
    def loadRequired(self, forceFirmware=False):
        """Load firmware file or FPGA file only as required, skip otherwise"""
        stdout = self.getStatus()
               
        if "OpenADC" not in stdout or forceFirmware:        
            #Load firmware
            self.loadFirmware()
            stdout = self.getStatus()
        else:
            if self.console:
                self.console.append("Skipped firmware download")    
        
        if "FPGA configured" not in stdout:
            self.loadFPGA()                 
        else:
            if self.console:
                self.console.append("Skipped FPGA download")     
            
    def loadFirmware(self):               
        """Load the USB microcontroller firmware file setup in the dialog"""
        cmd = "java -cp %s FWLoader -c -f -uu %s"%(self.fwLocation.text(), self.firmwareLocation.text())
        process = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        exit_code = process.wait()     
        if self.console:
            self.console.append(stdout)
            self.console.append(stderr)
    
    def loadFPGA(self):
        """Load the FPGA bitfile set up in the dialog"""        
        cmd = "java -cp %s FWLoader -f -uf %s"%(self.fwLocation.text(), self.bitLocation.text())
        process = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        exit_code = process.wait()        
        if self.console:
            self.console.append(stdout)
            self.console.append(stderr)        


class EncryptionStatusMonitor(QDialog):
    def __init__(self, parent):
        super(EncryptionStatusMonitor, self).__init__(parent)
        self.textResultsLayout = QGridLayout()
        self.textInLine = QLineEdit()
        self.textOutLine = QLineEdit()
        self.textResultsLayout.addWidget(QLabel("Text In "), 0, 0)
        self.textInLine.setReadOnly(True)
        self.textResultsLayout.addWidget(self.textInLine, 0, 1)
        self.textResultsLayout.addWidget(QLabel("Text Out"), 1, 0)
        self.textOutLine.setReadOnly(True)
        self.textResultsLayout.addWidget(self.textOutLine, 1, 1)
        self.textResultsLayout.addWidget(QLabel("Expected"), 2, 0)
        self.textOutExpected = QLineEdit()
        self.textOutExpected.setReadOnly(True)        
        self.textResultsLayout.addWidget(self.textOutExpected, 2, 1)
        self.setLayout(self.textResultsLayout)  
        self.hide()
               

class ChipWhispererCapture(MainChip):
    MaxRecentFiles = 4    
    def __init__(self):
        super(ChipWhispererCapture, self).__init__(name="ChipWhisperer Capture V2", imagepath=imagePath)
        self.console = self.addConsole()
    
        self.scope = None        
        self.trace = None
        self.setKey('2b 7e 15 16 28 ae d2 a6 ab f7 15 88 09 cf 4f 3c')
        #self.setKey('9B A5 A3 14 40 32 37 C8 CD 06 13 AA 88 62 49 6A')
        self.target = TargetInterface(log=self.console, showScriptParameter=self.showScriptParameter)        
        self.target.paramListUpdated.connect(self.reloadTargetParamList)
    
        valid_scopes = {"None":None, "ChipWhisperer/OpenADC":OpenADCInterface(parent=self, console=self.console, showScriptParameter=self.showScriptParameter)}        
        valid_traces = {"None":None, "ChipWhisperer/Native":TraceContainerNative, "DPAContestv3":TraceContainerDPAv3}#"DPA Contest v3": writer_dpav3.dpav3()}    
        
        self.esm = EncryptionStatusMonitor(self)
        
       
        
        self.cwParams = [
                {'name':'Scope Module', 'type':'list', 'values':valid_scopes, 'value':valid_scopes["None"], 'set':self.scopeChanged},
                self.target.toplevel_param,
                {'name':'Trace Format', 'type':'list', 'values':valid_traces, 'value':valid_traces["None"], 'set':self.traceChanged},
                
                {'name':'Key Settings', 'type':'group', 'children':[
                        {'name':'Encryption Key', 'type':'str', 'value':self.textkey, 'set':self.setKey},
                        {'name':'Send Key to Target', 'type':'bool', 'value':True},
                    ]},   
                         
                {'name':'Acquisition Settings', 'type':'group', 'children':[
                        {'name':'Number of Traces', 'type':'int', 'limits':(1, 1E6), 'value':100, 'set':self.setNumTraces, 'get':self.getNumTraces},
                        {'name':'Open Monitor', 'type':'action', 'action':self.esm.show},
                        {'name':'Fixed Plaintest', 'type':'bool', 'value':False, 'set':self.setFixedPlain }
                    ]}             
                ]
        
        self.da = None
        self.numTraces = 100

        self.addToolbars()
        self.addSettingsDocks()
        self.addWaveforms()
        self.addToolMenu()
        
        self.restoreDockGeometry()
        self.newProject()   
        
        self.newFile.connect(self.newProject)
        self.saveFile.connect(self.saveProject)   
        
        self.fixedPlain = False 
     
    def setFixedPlain(self, x):
        self.fixedPlain = x
        
    def getNumTraces(self):
        return self.numTraces
        
    def setNumTraces(self, t):
        self.numTraces = t      

    def setKey(self, key, binary=False, updateParamList=False):
        
        if binary:
            self.textkey = ''
            for s in key:
                self.textkey += '%02x '%s
            self.key = bytearray(key)
        else:        
            self.textkey = key       
            self.key = bytearray()
            for s in key.split():
                self.key.append(int(s, 16))
        
    def FWLoaderConfig(self):
        self.CWFirmwareConfig.show()
    
    def FWLoaderGo(self):
        self.CWFirmwareConfig.loadRequired()

    def addToolMenu(self):        
        self.CWFirmwareConfig = FWLoaderConfig(self, console=self.console)
        
        self.CWFirmwareConfigAct = QAction('Config CW Firmware', self,                               
                               statusTip='Configure ChipWhisperer FW Paths',
                               triggered=self.FWLoaderConfig)

        self.CWFirmwareGoAct = QAction('Download CW Firmware', self,                               
                               statusTip='Download Firmware+FPGA To Hardware',
                               triggered=self.FWLoaderGo)
        
        self.toolMenu.addAction(self.CWFirmwareConfigAct)
        self.toolMenu.addAction(self.CWFirmwareGoAct)
        self.toolMenu.addSeparator()

        
    def addWaveforms(self):
        self.waveformDock = self.addTraceDock("Capture Waveform (Channel 1)")
        
        #TODO: FIX THIS HACK
        #Should be something in ScopeInterface class maybe
        self.waveformDock.widget().setDefaultYRange(-0.5, 0.5)
        self.waveformDock.widget().YDefault()       
        
    def addSettingsDocks(self):      
        self.setupParametersTree()        
        self.settingsNormalDock = self.addSettings(self.paramTree, "General Settings")
        self.settingsScopeDock = self.addSettings(self.scopeParamTree, "Scope Settings")
        self.settingsTargetDock = self.addSettings(self.targetParamTree, "Target Settings")

    def setupParametersTree(self):
        self.params = Parameter.create(name='Generic Settings', type='group', children=self.cwParams)
        ExtendedParameter.setupExtended(self.params, self)
        self.paramTree = ParameterTree()
        self.paramTree.setParameters(self.params, showTop=False)
        
        self.scopeParamTree = ParameterTree()
        self.targetParamTree = ParameterTree()
                
    #def paramTreeChanged(self, param, changes):
    #    if self.showScriptParameter is not None:
    #        self.showScriptParameter(param, changes, self.params)
                
    def reloadScopeParamList(self, lst=None): 
        ExtendedParameter.reloadParams(self.scope.paramList(), self.scopeParamTree)              
        
    def reloadTargetParamList(self, lst=None):
        ExtendedParameter.reloadParams(self.target.paramList(), self.targetParamTree)
        
    def reloadParamList(self, lst=None):
        ExtendedParameter.reloadParams(self.paramList(), self.paramTree)
        
    def paramList(self):
        p = []
        p.append(self.params)     
        return p   

    def newScopeData(self,  data=None, offset=0):
        self.waveformDock.widget().passTrace(data, offset)

    def setConfigWidget(self, widget):
        self.configdock.setWidget(widget)

    def addToolbars(self):
        self.addCaptureTools()

    def addCaptureTools(self):
        capture1 = QAction(QIcon(imagePath+'play1.png'), 'Capture 1', self)
        capture1.triggered.connect(self.capture1)
        captureM = QAction(QIcon(imagePath+'playM.png'), 'Capture Multi', self)
        captureM.triggered.connect(self.captureM)
        
        self.captureStatus = QToolButton()
        self.captureStatusActionDis = QAction(QIcon(imagePath+'status_disconnected.png'),  'Status: Disconnected',  self)
        self.captureStatusActionDis.triggered.connect(self.doConDis)
        self.captureStatusActionCon = QAction(QIcon(imagePath+'status_connected.png'),  'Status: Connected',  self)
        self.captureStatus.setDefaultAction(self.captureStatusActionDis)

        self.CaptureToolbar = self.addToolBar('Capture Tools')
        self.CaptureToolbar.setObjectName('Capture Tools')
        self.CaptureToolbar.addAction(capture1)
        self.CaptureToolbar.addAction(captureM)
        self.CaptureToolbar.addWidget(self.captureStatus)
        #self.CaptureToolbar.setEnabled(False)
        
        

    def connected(self, status=True, text=None):
        #self.CaptureToolbar.setEnabled(status)
        
        if status:
            self.captureStatus.setDefaultAction(self.captureStatusActionCon)
        else:
            self.captureStatus.setDefaultAction(self.captureStatusActionDis)


    def doConDis(self):        
        if self.captureStatus.defaultAction() == self.captureStatusActionDis:      
            if self.scope is not None:
                try:
                    self.scope.con()
                    if self.scope is not None:
                        try:
                            self.target.setOpenADC(self.scope.qtadc.ser)
                        except:
                            pass        
                    self.target.con()
                    self.statusBar().showMessage("Connected :)")
                except IOError:
                    exctype, value = sys.exc_info()[:2]
                    self.console.append("Connect Error: %s"%(str(value)))
                    #QMessageBox.warning(None, "Connect Error", str(exctype) + str(value))  
                    
        else:
            if self.scope is not None:
                self.scope.dis()
            
            self.target.dis()

    def capture1(self):
        if self.target.driver:
            target = self.target.driver
        else:
            target = None
                     
        #Check key with target
        if target:
            self.setKey(target.checkEncryptionKey(self.key), True, True)
                     
        ac = acquisitionController(self.scope, target, writer=None, fixedPlain=self.fixedPlain, textInLabel=self.esm.textInLine, textOutLabel=self.esm.textOutLine, textExpectedLabel=self.esm.textOutExpected)
        ac.doSingleReading(key=self.key)
        self.statusBar().showMessage("One Capture Complete")

    def printTraceNum(self, num, data, offset=0):
        self.statusBar().showMessage("Trace %d done"%num)
        #self.newScopeData(data, offset)        

    def captureM(self):
        if self.target.driver:
            target = self.target.driver
        else:
            target = None
            
        #Check key with target
        if target:
            self.setKey(target.checkEncryptionKey(self.key), True, True)
            
        #Load trace writer
        if self.trace is not None:
            writer = self.trace()
            starttime = datetime.now()            
            prefix = starttime.strftime('%Y.%m.%d-%H.%M.%S_') 
            writer.config.setAttr("prefix", prefix)
            writer.config.setConfigFilename(self.proj.datadirectory + "traces/config_" + prefix + ".cfg")
            writer.config.setAttr("date", starttime.strftime('%Y-%m-%d %H:%M:%S'))
        else:
            writer = None
                    
        ac = acquisitionController(self.scope, target, writer, textInLabel=self.esm.textInLine, textOutLabel=self.esm.textOutLine, textExpectedLabel=self.esm.textOutExpected)
        ac.traceDone.connect(self.printTraceNum)
        tn = self.numTraces
        ac.setMaxtraces(tn)        
        ac.doReadings(addToList=self.manageTraces, key=self.key)
        self.statusBar().showMessage("%d Captures Completed"%tn)
        
        return writer
        
    def scopeChanged(self, newscope):        
        self.scope = newscope
        if self.scope is not None:
            self.scope.paramListUpdated.connect(self.reloadScopeParamList)                     
        self.reloadScopeParamList()
        
        self.scope.dataUpdated.connect(self.newScopeData)
        self.scope.connectStatus.connect(self.connected)
        
    def traceChanged(self, newtrace):
        self.trace = newtrace
        #TODO: Reload?
  
    def newProject(self):        
        self.proj = ProjectFormat()
        self.proj.setProgramName("ChipWhisperer-Capture")
        self.proj.setProgramVersion("2.00")
        self.proj.addParamTree(self)
        self.proj.addParamTree(self.scope)
        self.proj.addParamTree(self.target)      
        self.proj.setTraceManager(self.manageTraces)  
        self.setCurrentFile(None)
  
    def saveProject(self):
        if self.proj.hasFilename() == False:
            fname, _ = QFileDialog.getSaveFileName(self, 'Save New File','.','*.cwp')
            
            if fname is None:
                return
            
            self.proj.setFilename(fname)
            self.setCurrentFile(fname)
            
        self.proj.save()
        self.dirty = False
        self.updateTitleBar()
        self.statusBar().showMessage("Project Saved")
  
def makeApplication():
    # Create the Qt Application
    app = QApplication(sys.argv)
    app.setOrganizationName("ChipWhisperer")
    app.setApplicationName("Capture V2")
    return app
  
import gc
  
if __name__ == '__main__':
    app = makeApplication()
    
    gc.disable()
    
    # Create and show the form
    window = ChipWhispererCapture()
    window.show()
   
    # Run the main Qt loop
    sys.exit(app.exec_())
