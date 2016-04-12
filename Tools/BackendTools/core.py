#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Core Backend Tools in the BackendTools Package for WxFixBoot Version 2.0~pre1
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

#Begin Main Class.
class Main(): #*** These need refactoring and proper testing ***
    def UpdateChrootMtab(self, MountPoint):
        """Update /etc/mtab inside a chroot, so the list of mounted filesystems is always right.""" #*** Don't copy to /etc/mtab, as this may screw up mounting in target os later. Copy to MountPoint/proc/self/mounts. Actually, /proc is bound to /MountPoint/proc. What's not working with this command?! ***
        logger.debug("CoreBackendTools: Main().UpdateChrootMtab: Updating /etc/mtab for chroot at: "+MountPoint+"...")

        retval = CoreTools.StartProcess("cp -vf /proc/self/mounts "+MountPoint+"/etc/mtab", ShowOutput=False)

        if retval != 0:
            logger.error("CoreBackendTools: Main().UpdateChrootMtab(): Failed to run command: cp -vf /proc/self/mounts "+MountPoint+"/etc/mtab! Chroot may not set up properly! This *probably* doesn't matter, but in rare situations it could cause problems.")

        logger.debug("CoreBackendTools: Main().UpdateChrootMtab: Finished updating /etc/mtab for chroot at: "+MountPoint+".")

    def SetUpChroot(self, MountPoint): #*** Test this again *** *** Return retval ***
        """Set up a chroot for the given mountpoint."""
        logger.debug("CoreBackendTools: Main().SetUpChroot(): Setting up chroot for MountPoint: "+MountPoint+"...")

        #Mount /dev, /dev/pts, /proc and /sys for the chroot.
        #We might also need internet access in chroot, so to do this first backup MountPoint/etc/resolv.conf to MountPoint/etc/resolv.conf.bak (if it's a link, this will also preserve it),
        #then copy current system's /etc/resolv.conf (the contents, not the link) to MountPoint/etc/resolv.conf, enabling internet access.

        MountList = ("/dev", "/dev/pts", "/proc", "/sys")
        for FileSystem in MountList:
            if CoreTools.MountPartition(Partition=FileSystem, MountPoint=MountPoint+FileSystem, Options="--bind") != 0:
                logger.error("CoreBackendTools: Main().SetUpChroot(): Failed to bind "+FileSystem+" to "+MountPoint+Filesystem+"! Chroot isn't set up properly! Attempting to continue anyway...") #*** What shall we do here? ***

        ExecList = ("mv -vf "+MountPoint+"/etc/resolv.conf "+MountPoint+"/etc/resolv.conf.bak", "cp -fv /etc/resolv.conf "+MountPoint+"/etc/resolv.conf")
        for ExecCmd in ExecList:
            Result = CoreTools.StartProcess(ExecCmd, ShowOutput=False, ReturnOutput=True)
            output = Result[1]
            retval = Result[0]

            if retval != 0:
                logger.error("CoreBackendTools: Main().SetUpChroot(): Error: Failed to run command: "+', '.join(ExecList)+"! Chroot may not be set up properly!")

        self.UpdateChrootMtab(MountPoint=MountPoint)

        logger.debug("CoreBackendTools: Main().SetUpChroot(): Finished setting up chroot for MountPoint: "+MountPoint+"...")

    def TearDownChroot(self, MountPoint): #*** Test this again *** *** Return Retval ***
        """Remove a chroot at the given mountpoint."""
        logger.debug("CoreBackendTools: Main().TearDownChroot(): Removing chroot at MountPoint: "+MountPoint+"...")

        #Unmount /dev/pts, /dev, /proc and /sys in the chroot.
        UnmountList = (MountPoint+"/dev/pts", MountPoint+"/dev", MountPoint+"/proc", MountPoint+"/sys")

        for FileSystem in UnmountList:
            if CoreTools.Unmount(FileSystem) != 0:
                logger.error("CoreBackendTools: Main().TearDownChroot(): Faied to unmount "+FileSystem+"! Chroot isn't removed properly! Attempting to continue anyway...") #*** What do we do here? ***

        #We'll also need to replace the MountPoint/etc/resolv.conf with the backup file, MountPoint/etc/resolv.conf.bak.
        Retval = CoreTools.StartProcess("mv -vf "+MountPoint+"/etc/resolv.conf.bak "+MountPoint+"/etc/resolv.conf", ShowOutput=False)

        if Retval != 0:
            logger.error("CoreBackendTools: Main().TearDownChroot(): Failed to run command: 'mv -vf "+MountPoint+"/etc/resolv.conf.bak "+MountPoint+"/etc/resolv.conf'! Return value was: "+Retval+". Chroot may not be removed properly!") #*** What do we do here? ***

        logger.debug("CoreBackendTools: Main().TearDownChroot(): Finished removing chroot at MountPoint: "+MountPoint+"...")

    def GetDeviceID(self, Device):
        """Retrive the given partition's/device's ID.""" #*** Will be removed/moved to startuptools soon after switching to dictionaries *** *** Give full path? ***
        logger.info("CoreBackendTools: Main().GetDeviceID(): Getting ID for partition/device: "+Device+"...")

        Temp = CoreTools.StartProcess("ls -l /dev/disk/by-id/", ShowOutput=False, ReturnOutput=True)
        retval = Temp[0]
        output = Temp[1].split('\n')

        if retval != 0:
            #We couldn't find the ID! Return "None".
            logger.warning("CoreBackendTools: Main().GetDeviceID(): Couldn't find ID for partition/device: "+Device+"! This may cause problems down the line.")
            return "None"

        else:
            #Try to get the ID from ls's output.
            ID = "None"

            for line in output:
                try:
                    SplitLine = line.split()
                    if "../../"+Device.split('/')[-1] == SplitLine[-1]:
                        ID = SplitLine[-3]
                except:
                    pass

            if ID != "None":
                logger.info("CoreBackendTools: Main().GetDeviceID(): Found ID ("+ID+") for partition/device: "+Device+"...")

            else:
                logger.warning("CoreBackendTools: Main().GetDeviceID(): Couldn't find ID for partition/device: "+Device+"! This may cause problems down the line.")

            return ID

#End main Class.
