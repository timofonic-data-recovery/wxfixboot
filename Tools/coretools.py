#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Core Tools in the Tools Package for WxFixBoot Version 2.0~pre2
# This file is part of WxFixBoot.
# Copyright (C) 2013-2016 Hamish McIntyre-Bhatty
# WxFixBoot is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 or,
# at your option, any later version.
#
# WxFixBoot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WxFixBoot.  If not, see <http://www.gnu.org/licenses/>.

#Do future imports to prepare to support python 3. Use unicode strings rather than ASCII strings, as they fix potential problems.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

#Filter warnings as errors.
import warnings
warnings.filterwarnings("error")

#Begin Main Class.
class Main():
    def StartProcess(self, ExecCmds, StdinLines=[], ShowOutput=True, ReturnOutput=False): #*** ShowOutput is ignored currently ***
        """Start a process given a string of commands to execute.
        ShowOutput is boolean and specifies whether to show output in the outputbox (if exists) or not.
        ReturnOutput is boolean and specifies whether to return the output back to the caller or not.
        """
        #Make sure output is always in English.
        ExecCmds = "LC_ALL=C "+ExecCmds

        #Get ready to run the command(s). Read up to 100 empty "" characters after the process finishes to make sure we get all the output.
        Counter = 0
        Line = str("")
        LineList = []

        #Run the command(s).
        logger.debug("CoreTools: Main().StartProcess(): Starting process: "+ExecCmds)
        cmd = subprocess.Popen(ExecCmds, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

        #If we have any lines to write to stdin, do that now. *** Check this works *** *** Do we need this, and if not shall we keep it anyway for future-proofing? ***
        if StdinLines != []:
            for Line in StdinLines:
                cmd.stdin.write(Line+"\n")

        #Close stdin (some programs wait for this before they will exit).
        cmd.stdin.close()

        while cmd.poll() == None or Counter < 100:
            Char = cmd.stdout.read(1)

            if cmd.poll() != None and Char == "":
                Counter += 1
                break

            Line += Char

            try:
                if Char in ("\n", "\r"):
                    #Convert to unicode if needed and remove "NULL" characters.
                    if unicode(type(Line)) != type(""):
                        Line = unicode(Line, errors="replace").replace("\x00", "")

                    wx.CallAfter(ParentWindow.UpdateOutputBox, Line)
                    LineList.append(Line.replace("\n", "").replace("\r", ""))

                    #Reset Line.
                    Line = str("")

            except UnicodeWarning:
                pass

        #Save runcmd.returncode, as it tends to reset fairly quickly.
        Retval = int(cmd.returncode)

        #Log this info in a debug message.
        logger.debug("CoreTools: Main().StartProcess(): Process: "+ExecCmds+": Return Value: "+unicode(Retval)+", Output: \"\n\n"+'\n'.join(LineList)+"\"\n")

        if ReturnOutput == False:
            #Return the return code back to whichever function ran this process, so it can handle any errors.
            return Retval

        else:
            #Return the return code, as well as the output.
            return (Retval, '\n'.join(LineList))

    def IsMounted(self, Partition, MountPoint=None):
        """Checks if the given partition is mounted.
        Partition is the given partition to check.
        If MountPoint is specified, check if the partition is mounted there, rather than just if it's mounted.
        Return boolean True/False.
        """
        if MountPoint == None:
            logger.debug("CoreTools: Main().IsMounted(): Checking if "+Partition+" is mounted...")
            MountInfo = self.StartProcess("mount -l", ReturnOutput=True)[1]

            Mounted = False

            for Line in MountInfo.split("\n"):
                if Line.split()[0] == Partition:
                    Mounted = True

        else:
            #Check where it's mounted to.
            logger.debug("CoreTools: Main().IsMounted(): Checking if "+Partition+" is mounted at "+MountPoint+"...")

            Mounted = False

            if self.GetMountPointOf(Partition) == MountPoint:
                Mounted = True

        if Mounted:
            logger.debug("CoreTools: Main().IsMounted(): It is. Returning True...")
            return True

        else:
            logger.debug("CoreTools: Main().IsMounted(): It isn't. Returning False...")
            return False

    def GetPartitionMountedAt(self, MountPoint):
        """Returns the partition mounted at the given mountpoint, if any.
        Otherwise, return None"""
        logger.info("CoreTools: Main().GetPartitionMountedAt(): Trying to get partition mounted at "+MountPoint+"...")

        MountInfo = self.StartProcess("mount -l", ReturnOutput=True)[1]
        Partition = None

        for Line in MountInfo.split("\n"):
            SplitLine = Line.split()

            if MountPoint == SplitLine[2]:
                Partition = SplitLine[0]

        if Partition != None:
            logger.info("CoreTools: Main().GetPartitionMountedAt(): Found it! Partition is "+Partition+"...")

        else:
            logger.info("CoreTools: Main().GetPartitionMountedAt(): Didn't find it...")

        return Partition

    def GetMountPointOf(self, Partition):
        """Returns the mountpoint of the given partition, if any.
        Otherwise, return None"""
        logger.info("CoreTools: Main().GetMountPointOf(): Trying to get mount point of partition "+Partition+"...")

        MountInfo = self.StartProcess("mount -l", ReturnOutput=True)[1]
        MountPoint = None

        for Line in MountInfo.split("\n"):
            SplitLine = Line.split()

            if Partition == SplitLine[0]:
                MountPoint = SplitLine[2]

        if MountPoint != None:
            logger.info("CoreTools: Main().GetMountPointOf(): Found it! MountPoint is "+MountPoint+"...")

        else:
            logger.info("CoreTools: Main().GetMountPointOf(): Didn't find it...")

        return MountPoint

    def MountPartition(self, Partition, MountPoint, Options=""):
        """Mounts the given partition.
        Partition is the partition to mount.
        MountPoint is where you want to mount the partition.
        Options is non-mandatory and contains whatever options you want to pass to the mount command.
        The default value for Options is an empty string.
        """
        if Options != "":
            logger.info("CoreTools: Main().MountPartition(): Preparing to mount "+Partition+" at "+MountPoint+" with extra options "+Options+"...")

        else:
            logger.info("CoreTools: Main().MountPartition(): Preparing to mount "+Partition+" at "+MountPoint+" with no extra options...")
            
        MountInfo = self.StartProcess("mount -l", ReturnOutput=True)[1]

        #There is a partition mounted here. Check if our partition is already mounted in the right place.
        if MountPoint == self.GetMountPointOf(Partition):
            #The correct partition is already mounted here.
            logger.debug("CoreTools: Main().MountPartition(): Partition: "+Partition+" was already mounted at: "+MountPoint+". Continuing...")
            return 0

        elif MountPoint in MountInfo:
            #Something else is in the way. Unmount that partition, and continue.
            logger.warning("CoreTools: Main().MountPartition(): Unmounting filesystem in the way at "+MountPoint+"...")
            Retval = self.Unmount(MountPoint)

            if Retval != 0:
                logger.error("CoreTools: Main().MountPartition(): Couldn't unmount "+MountPoint+", preventing the mounting of "+Partition+"! Skipping mount attempt.")
                return False

        #Create the dir if needed.
        if os.path.isdir(MountPoint) == False:
            os.makedirs(MountPoint)
    
        #Mount the device to the mount point.
        Retval = self.StartProcess("mount "+Options+" "+Partition+" "+MountPoint)

        if Retval == 0:
            logger.debug("CoreTools: Main().MountPartition(): Successfully mounted partition!")

        else:
            logger.warning("CoreTools: Main().MountPartition(): Failed to mount partition!")

        return Retval

    def RemountPartition(self, Partition, Mode="rw"):
        """Remounts the given partition.
        Partition is the partition to remount.
        Mode is non-mandatory and is either rw or ro for read-write or read-only respectively.
        The default value for Mode is rw.
        """
        logger.debug("CoreTools: Main().RemountPartition(): Remounting "+Partition+" as "+Mode+"...")
        Retval = self.StartProcess("mount -o remount,"+Mode+" "+Partition, ShowOutput=False)

        if Retval == 0:
            logger.warning("CoreTools: Main().RemountPartition(): Successfully remounted partition!")

        else:
            logger.info("CoreTools: Main().RemountPartition(): Failed to remount partition!")

        #Return the return value
        return Retval

    def Unmount(self, MountPoint):
        """Unmounts the given mountpoint.
        MountPoint is the mountpoint to unmount.
        MountPoint can also be a partition name (for example /dev/sda1).
        """
        logger.debug("CoreTools: Main().Unmount(): Preparing to unmount "+MountPoint)

        if MountPoint not in self.StartProcess("mount -l", ReturnOutput=True)[1]:
            logger.info("CoreTools: Main().Unmount(): "+MountPoint+" was not mounted. Continuing...")
            Retval = 0

        else:
            logger.debug("CoreTools: Main().Unmount(): Unmounting "+MountPoint+"...")
            Retval = self.StartProcess("umount "+MountPoint, ShowOutput=False)

            if Retval == 0:
                logger.info("CoreTools: Main().Unmount(): Successfully unmounted "+MountPoint+"!")

            else:
                logger.warning("CoreTools: Main().Unmount(): Failed to unmount "+MountPoint+"!")
            
        #Return the return value
        return Retval

    def Find(self, RegExp, TopLevelDirectory):
        """Finds the given file, somewhere in or below the given directory, and returns True or False depending on if it was found or not"""
        logger.info("CoreTools: Main().Find(): Looking in "+TopLevelDirectory+" with regular expression "+RegExp+"...")
        FilesFound = []
        for Root, Directory, Files in os.walk(TopLevelDirectory):
            #Convert unicode strings in a list with one element.
            if unicode(type(Files)) == type(""):
                Files = [Files]

            #Check each file.
            for File in Files:
                if re.match(RegExp, File, re.M|re.I) is not None:
                    FilesFound.append(os.path.join(Root, File))

        if FilesFound != []:
            logger.info("CoreTools: Main().Find(): Found files "+' '.join(FilesFound)+"...")

        else:
            logger.info("CoreTools: Main().Find() Didn't find any files...")

        return FilesFound

    def UpdateChrootMtab(self, MountPoint):
        """Update /etc/mtab inside a chroot, so the list of mounted filesystems is always right."""
        logger.debug("CoreTools: Main().UpdateChrootMtab(): Updating /etc/mtab for chroot at: "+MountPoint+"...")

        retval = CoreTools.StartProcess("cp -vf /proc/self/mounts "+MountPoint+"/etc/mtab", ShowOutput=False)

        if retval != 0:
            logger.error("CoreTools: Main().UpdateChrootMtab(): Failed to run command: cp -vf /proc/self/mounts "+MountPoint+"/etc/mtab! Chroot may not set up properly! This *probably* doesn't matter, but in rare situations it could cause problems.")

        logger.debug("CoreTools: Main().UpdateChrootMtab(): Finished updating /etc/mtab for chroot at: "+MountPoint+".")

    def SetUpChroot(self, MountPoint):
        """Set up a chroot for the given mountpoint."""
        logger.debug("CoreTools: Main().SetUpChroot(): Setting up chroot for MountPoint: "+MountPoint+"...")

        #Mount /dev, /dev/pts, /proc and /sys for the chroot.
        #We might also need internet access in chroot, so to do this first backup MountPoint/etc/resolv.conf to MountPoint/etc/resolv.conf.bak (if it's a link, this will also preserve it),
        #then copy current system's /etc/resolv.conf (the contents, not the link) to MountPoint/etc/resolv.conf, enabling internet access.

        MountList = ("/dev", "/dev/pts", "/proc", "/sys")
        for FileSystem in MountList:
            if CoreTools.MountPartition(Partition=FileSystem, MountPoint=MountPoint+FileSystem, Options="--bind") != 0:
                logger.error("CoreTools: Main().SetUpChroot(): Failed to bind "+FileSystem+" to "+MountPoint+Filesystem+"! Chroot isn't set up properly! Attempting to continue anyway...") #*** What shall we do here? ***

        ExecList = ("mv -vf "+MountPoint+"/etc/resolv.conf "+MountPoint+"/etc/resolv.conf.bak", "cp -fv /etc/resolv.conf "+MountPoint+"/etc/resolv.conf")
        for ExecCmd in ExecList:
            Result = CoreTools.StartProcess(ExecCmd, ShowOutput=False, ReturnOutput=True)
            output = Result[1]
            Retval = Result[0]

            if Retval != 0:
                logger.error("CoreTools: Main().SetUpChroot(): Error: Failed to run command: "+', '.join(ExecList)+"! Chroot may not be set up properly!")

        self.UpdateChrootMtab(MountPoint=MountPoint)

        logger.debug("CoreTools: Main().SetUpChroot(): Finished setting up chroot for MountPoint: "+MountPoint+"...")
        return Retval

    def TearDownChroot(self, MountPoint):
        """Remove a chroot at the given mountpoint."""
        logger.debug("CoreTools: Main().TearDownChroot(): Removing chroot at MountPoint: "+MountPoint+"...")

        #Unmount /dev/pts, /dev, /proc and /sys in the chroot.
        UnmountList = (MountPoint+"/dev/pts", MountPoint+"/dev", MountPoint+"/proc", MountPoint+"/sys")

        for FileSystem in UnmountList:
            if CoreTools.Unmount(FileSystem) != 0:
                logger.error("CoreTools: Main().TearDownChroot(): Faied to unmount "+FileSystem+"! Chroot isn't removed properly! Attempting to continue anyway...") #*** What do we do here? ***

        #We'll also need to replace the MountPoint/etc/resolv.conf with the backup file, MountPoint/etc/resolv.conf.bak.
        Retval = CoreTools.StartProcess("mv -vf "+MountPoint+"/etc/resolv.conf.bak "+MountPoint+"/etc/resolv.conf", ShowOutput=False)

        if Retval != 0:
            logger.error("CoreTools: Main().TearDownChroot(): Failed to run command: 'mv -vf "+MountPoint+"/etc/resolv.conf.bak "+MountPoint+"/etc/resolv.conf'! Return value was: "+Retval+". Chroot may not be removed properly!") #*** What do we do here? ***

        logger.debug("CoreTools: Main().TearDownChroot(): Finished removing chroot at MountPoint: "+MountPoint+"...")
        return Retval

    def EmergencyExit(self, Message):
        """Handle emergency exits. Warn the user, log, and exit to terminal with the given message"""
        logger.critical("CoreTools: Main().EmergencyExit(): Emergency exit has been triggered! Giving user message dialog and saving the logfile...")
        logger.critical("CoreTools: Main().EmergencyExit(): The error is: "+Message)

        #Warn the user.
        DialogTools.ShowMsgDlg(Message="Emergency exit triggered.\n\n"+Message+"\n\nYou'll now be asked for a location to save the log file.\nIf you email me at hamishmb@live.co.uk with the contents of that file I'll be willing to help you fix this problem.", Kind="error")

        #Shut down the logger.
        logging.shutdown()

        #Save the log file.
        LogFile = DialogTools.ShowSaveFileDlg(Wildcard="Log Files|*.log")
        self.StartProcess("mv -v /tmp/wxfixboot.log "+LogFile)

        #Exit.
        DialogTools.ShowMsgDlg(Message="Done. WxFixBoot will now exit.")
        wx.Exit()
        sys.exit(Message)

#End main Class.
