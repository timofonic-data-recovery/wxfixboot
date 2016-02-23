#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Main Backend Tools in the BackendTools Package for WxFixBoot Version 1.1~pre1
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
class Main():
    def GetOldBootloaderConfig(self): #*** Add more logging messages ***
        """Get the old bootloader's config before removing it, so we can reuse it (if possible) with the new one."""
        logger.debug("MainBackendTools: Main().GetOldBootloaderConfig(): Preparing to get bootloader config...")
        wx.CallAfter(ParentWindow.UpdateCurrentOpText, Message="Preparing to get bootloader config...")
        wx.CallAfter(ParentWindow.UpdateCurrentProgress, 2)
        wx.CallAfter(ParentWindow.UpdateOutputBox, "\n###Preparing to get old bootloader config...###\n")

        #Define global vars
        global BootloaderTimeout
        global KernelOptions

        #Use two lists for global kernel options and timeouts, so if they differ for each instance of the bootloader (assuming there is more than one), we can ask the user which is best, or go with WxFixBoot's default (timeout=10, kopts="quiet splash nomodeset")
        KernelOptsList = []
        TimeoutsList = []

        #Set two temporary vars.
        timeout = ""
        kopts = ""

        wx.CallAfter(ParentWindow.UpdateCurrentOpText, Message="Getting old bootloader config...")
        wx.CallAfter(ParentWindow.UpdateOutputBox, "\n###Getting old bootloader config...###\n")

        #Loop through each OS in OSsForBootloaderRemoval, and provide information to the function that gets the configuration.
        logger.info("MainBackendTools: Main().GetOldBootloaderConfig(): Looking for configuration in OSs marked for bootloader removal...")
        for OS in OSsForBootloaderRemoval:
            #Grab the OS's partition.
            Partition = OS.split()[-5]
            logger.debug("MainBackendTools: Main().GetOldBootloaderConfig(): Looking for config in OS: "+OS+"...")

            #Check if the Partition is AutoRootFS, if we're not on a live disk.
            if LiveDisk == False and Partition == AutoRootFS:
                #If so, make sure this will work for this OS too, and avoid setting mountpoint, so the config instructions below look in the right place for the config files.
                MountPoint = ""

            else:
                #If not, set mountpoint to the actual mountpoint.
                MountPoint = "/mnt"+Partition

                #Mount the partition.
                Retval = CoreTools().MountPartition(Partition=Partition, MountPoint=MountPoint)

                #Check if anything went wrong.
                if Retval != 0:
                    #Ignore this partition.
                    logger.warning("MainBackendTools: Main().GetOldBootloaderConfig(): Failed to mount "+Partiton+"! Ignoring this partition...")
                    continue

            #Look for the configuration file, based on which GetConfig() function we're about to run.
            if Bootloader == "GRUB-LEGACY":
                #Check MountPoint/boot/grub/menu.lst exists.
                if os.path.isfile(MountPoint+"/boot/grub/menu.lst"):
                    #It does, we'll run the function to find the config now.
                    timeout = GetConfigBootloaderTools().GetGRUBLEGACYConfig(filetoopen=MountPoint+"/boot/grub/menu.lst")
                    
            elif Bootloader in ('GRUB2', 'GRUB-UEFI'):
                #Check MountPoint/etc/default/grub exists, which should be for either GRUB2 or GRUB-UEFI.
                if os.path.isfile(MountPoint+"/etc/default/grub"):
                    #It does, we'll run the function to find the config now.
                    Temp = GetConfigBootloaderTools().GetGRUB2Config(filetoopen=MountPoint+"/etc/default/grub")
                    timeout = Temp[0]
                    kopts = Temp[1]

            elif Bootloader in ('LILO', 'ELILO'):
                #Check the config file exists for both lilo and elilo.
                if Bootloader == "LILO" and os.path.isfile(MountPoint+"/etc/lilo.conf"):
                    #It does, we'll run the function to find the config now.
                    Temp = GetConfigBootloaderTools().GetLILOConfig(filetoopen=MountPoint+"/etc/lilo.conf")
                    timeout = Temp[0]
                    kopts = Temp[1]

                elif Bootloader == "ELILO" and os.path.isfile(MountPoint+"/etc/elilo.conf"):
                    #It does, we'll run the function to find the config now.
                    Temp = GetConfigBootloaderTools().GetLILOConfig(filetoopen=MountPoint+"/etc/elilo.conf")
                    timeout = Temp[0]
                    kopts = Temp[1]

            #Unmount the partition, if needed.
            if MountPoint != "":
                CoreTools().Unmount(MountPoint) #*** Check it worked! ***

            #Now we have the config, let's add it to the list, if it's unique. This will also catch the NameError exception created if the bootloader's config file wasn't found. 
            #First do timeout.
            if timeout != "":
                try:
                    TimeoutsList.index(timeout)

                except ValueError:
                    #It's unique.
                    TimeoutsList.append(timeout)

                except NameError: pass

            if kopts != "":
                #Now kopts.
                try:
                    KernelOptsList.index(kopts)

                except ValueError:
                    #It's unique.
                    KernelOptsList.append(kopts)

                except NameError: pass

            wx.CallAfter(ParentWindow.UpdateCurrentProgress, 2+(14/len(OSsForBootloaderRemoval)))

        #We're finished getting the config.
        logger.info("MainBackendTools: Main().GetOldBootloaderConfig(): Finished looking for configuration in OSs marked for bootloader removal.")
        wx.CallAfter(ParentWindow.UpdateCurrentOpText, Message="Determining configuration to use...")
        wx.CallAfter(ParentWindow.UpdateCurrentProgress, 14)

        #Now let's check how many options there are in each of these lists, and run different code accordingly.
        #First TimeoutsList, but only if we aren't using a preset value for BootloaderTimeout.
        if BootloaderTimeout == -1:
            if len(TimeoutsList) == 0:
                #No timeout was found!
                Temp = DialogTools().ShowTextEntryDlg(Message="WxFixBoot couldn't find the currently installed bootloader's timeout value. Please enter a value, or use WxFixBoot's default (10).", Title="WxFixBoot - Enter timeout value")
                BootloaderTimeout = int(Temp)
                logger.info("MainBackendTools: Main().GetOldBootloaderConfig(): Using user's bootloader timeout value: "+unicode(BootloaderTimeout))

            elif len(TimeoutsList) == 1:
                #As there is one, do what the user said, and set it directly.
                BootloaderTimeout = int(TimeoutsList[0])
                logger.info("MainBackendTools: Main().GetOldBootloaderConfig(): Using only bootloader timeout value found: "+unicode(BootloaderTimeout))

            else:
                #Ask the user which timeout to use, as there are more than one.
                TimeoutsList.append("WxFixBoot's Default (10)")
                Result = DialogTools().ShowChoiceDlg(Message="WxFixBoot found multiple timeout settings. Please select the one you want.", Title="WxFixBoot -- Select Timeout Setting", Choices=TimeoutsList)

                #Save it.
                if Result == "WxFixBoot's Default (10)":
                    BootloaderTimeout = 10
                    logger.info("MainBackendTools: Main().GetOldBootloaderConfig(): Using WxFixBoot's default bootloader timeout value: 10")

                else:
                    BootloaderTimeout = int(Result)
                    logger.info("MainBackendTools: Main().GetOldBootloaderConfig(): Using user chosen bootloader timeout value: "+unicode(BootloaderTimeout))

        wx.CallAfter(ParentWindow.UpdateCurrentProgress, 21)

        #Now do the kernel options.
        if len(KernelOptsList) == 0:
            #No kernel options were found!
            #Ask the user to use WxFixBoot's default, or do manual config.
            Result = DialogTools().ShowYesNoDlg(Message="WxFixBoot couldn't find the current bootloader's default kernel options. Do you want to use WxFixBoot's default options? You should click yes and use the defaults, which are almost always fine. However, if you know exactly what you're doing, you can click no, and modify them yourself.", Title="WxFixBoot - Use Default Kernel Options?")

            if Result:
                KernelOptions = "quiet splash nomodeset"
                logger.info("MainBackendTools: Main().GetOldBootloaderConfig(): Using WxFixBoot's default kernel options: 'quiet splash nomodeset'")

            else:
                #Ask the user for the kernel options to use.
                Result = DialogTools().ShowTextEntryDlg(Message="Please enter the kernel options you want to use. WxFixBoot's default kernel options are: 'quiet splash nomodeset'. If you've changed your mind, type these instead.", Title="WxFixBoot - Enter Kernel Options")

                KernelOptions = Result
                logger.info("MainBackendTools: Main().GetOldBootloaderConfig(): Using user defined kernel options: '"+KernelOptions+"'")

        elif len(KernelOptsList) == 1:
            #Use the single set of options found.
            KernelOptions = KernelOptsList[0]
            logger.info("MainBackendTools: Main().GetOldBootloaderConfig(): Using only kernel options found: "+KernelOptions)

        else:
            #Ask the user which timeout to use, as there are more than one.
            KernelOptsList.append("WxFixBoot's Default ('quiet splash nomodeset')")
            Result = DialogTools().ShowChoiceDlg(Message="WxFixBoot found multiple kernel options. Please select the one you want.", Title="WxFixBoot -- Select Kernel Options", Choices=KernelOptsList)

            #Save it.
            if Result == "WxFixBoot's Default ('quiet splash nomodeset')":
                KernelOptions = "quiet splash nomodeset"
                logger.info("MainBackendTools: Main().GetOldBootloaderConfig(): Using WxFixBoot's default kernel options: 'quiet splash nomodeset'")

            else:
                KernelOptions = Result
                logger.warning("MainBackendTools: Main().GetOldBootloaderConfig(): Using user entered kernel options: "+KernelOptions)

        wx.CallAfter(ParentWindow.UpdateCurrentProgress, 25)

    def RemoveOldBootloader(self): #*** Reduce code duplication if possible *** *** Handle return values ***
        """Remove the currently installed bootloader."""
        logger.debug("MainBackendTools: Main().RemoveOldBootloader(): Preparing to remove old bootloaders...")
        wx.CallAfter(ParentWindow.UpdateCurrentOpText, Message="Removing old bootloaders...")
        wx.CallAfter(ParentWindow.UpdateCurrentProgress, 27)
        wx.CallAfter(ParentWindow.UpdateOutputBox, "\n###Removing old bootloaders...###\n")

        #Loop through each OS in OSsForBootloaderRemoval, and provide information to the function that will remove the bootloader.
        for OS in OSsForBootloaderRemoval:
            #For each OS that needs the bootloader removed, grab the partition, and the package manager.
            Partition = OS.split()[-5]
            PackageManager = OS.split()[-1]

            logger.info("MainBackendTools: Main().RemoveOldBootloader(): Removing "+Bootloader+" from OS: "+OS+"...")
            wx.CallAfter(ParentWindow.UpdateOutputBox, "\n###Removing the old bootloader from OS: "+OS+"...###\n")

            #Grab the architecture.
            Arch = OS.split()[-8]
            if Arch == "64-bit":
                Arch = "x86_64"

            else:
                Arch = "i686"
            
            #If we're not on a live disk, and the partition is AutoRootFS, let the remover function know that we aren't using chroot.
            if LiveDisk == False and Partition == AutoRootFS:
                if Bootloader == "GRUB-LEGACY":
                    retval = BootloaderRemovalTools().RemoveGRUBLEGACY(PackageManager=PackageManager, UseChroot=False, Arch=Arch)

                elif Bootloader == "GRUB2":
                    retval = BootloaderRemovalTools().RemoveGRUB2(PackageManager=PackageManager, UseChroot=False, Arch=Arch)

                elif Bootloader == "LILO":
                    retval = BootloaderRemovalTools().RemoveLILO(PackageManager=PackageManager, UseChroot=False, Arch=Arch)

                elif Bootloader == "GRUB-UEFI":
                    retval = BootloaderRemovalTools().RemoveGRUBUEFI(PackageManager=PackageManager, UseChroot=False, Arch=Arch)

                elif Bootloader == "ELILO":
                    retval = BootloaderRemovalTools().RemoveELILO(PackageManager=PackageManager, UseChroot=False, Arch=Arch)

            #Otherwise, setup the chroot and everything else first, and tell it we are using chroot, and pass the mountpoint to it.
            else:
                #Mount the partition using the global mount function.
                MountPoint = "/mnt"+Partition
                Retval = CoreTools().MountPartition(Partition=Partition, MountPoint=MountPoint)

                if Retval != 0:
                    logger.error("MainBackendTools: Main().RemoveOldBootloader(): Failed to remount "+Partition+"! Warn the user and skip this OS.")
                    DialogTools().ShowMsgDlg(Kind="error", Message="WxixBoot failed to mount the partition containing: "+OS+"! This OS will now be skipped.")

                else:
                    #Set up chroot.
                    CoreBackendTools().SetUpChroot(MountPoint=MountPoint)

                    #If there's a seperate /boot partition for this OS, make sure it's mounted. *** Read this OS's FSTAB instead of hoping that this works, cos then we can use the global mount function to do this *** *** this might mount other stuff and interfere too ***
                    CoreBackendTools().StartThreadProcess(['chroot', MountPoint, 'mount', '-av'], ShowOutput=False)

                    #Remove the bootloader.
                    if Bootloader == "GRUB-LEGACY":
                        retval = BootloaderRemovalTools().RemoveGRUBLEGACY(PackageManager=PackageManager, UseChroot=True, MountPoint=MountPoint, Arch=Arch)

                    elif Bootloader == "GRUB2":
                        retval = BootloaderRemovalTools().RemoveGRUB2(PackageManager=PackageManager, UseChroot=True, MountPoint=MountPoint, Arch=Arch)

                    elif Bootloader == "LILO":
                        retval = BootloaderRemovalTools().RemoveLILO(PackageManager=PackageManager, UseChroot=True, MountPoint=MountPoint, Arch=Arch)

                    elif Bootloader == "GRUB-UEFI":
                        retval = BootloaderRemovalTools().RemoveGRUBUEFI(PackageManager=PackageManager, UseChroot=True, MountPoint=MountPoint, Arch=Arch)

                    elif Bootloader == "ELILO":
                        retval = BootloaderRemovalTools().RemoveELILO(PackageManager=PackageManager, UseChroot=True, MountPoint=MountPoint, Arch=Arch)

                    #Tear down chroot.
                    CoreBackendTools().TearDownChroot(MountPoint=MountPoint)

            wx.CallAfter(ParentWindow.UpdateOutputBox, "\n###Finished removing the old bootloader from OS: "+OS+"...###\n")

            if retval != 0:
                #Something went wrong! Log it and notify the user.
                logger.error("MainBackendTools: Main().RemoveOldBootloader(): Failed to remove "+Bootloader+" from OS: "+OS+"! We'll continue anyway. Warn the user.")
                DialogTools().ShowMsgDlg(Kind="error", Message="WxFixBoot failed to remove "+Bootloader+" from: "+OS+"! This probably doesn't matter; when we install the new bootloader, it should take precedence over the old one anyway. Make sure you check that OS after WxFixBoot finishes its operations.")

            wx.CallAfter(ParentWindow.UpdateCurrentProgress, 27+(22/len(OSsForBootloaderRemoval)))

        #Log and notify the user that we're finished remving bootloaders.
        logger.info("MainBackendTools: Main().RemoveOldBootloader(): Finished removing bootloaders...")
        wx.CallAfter(ParentWindow.UpdateCurrentOpText, Message="Finished removing old bootloaders...")
        wx.CallAfter(ParentWindow.UpdateCurrentProgress, 50)
        DialogTools().ShowMsgDlg(Kind="info", Message="Finished removing old bootloaders! WxFixBoot will now install your new bootloader to: "+', '.join(OSsForBootloaderInstallation)+".")

    def InstallNewBootloader(self): #*** Reduce code duplication ***
        """Install a new bootloader."""
        wx.CallAfter(ParentWindow.UpdateCurrentOpText, Message="Preparing to install the new bootloader(s)...") #*** Does this need to be here? ***
        wx.CallAfter(ParentWindow.UpdateCurrentProgress, 52)  
        BootloaderInstallSucceded = True     

        #Loop through OSsForBootloaderInstallation, and provide information to the function that will install the bootloader.
        for OS in OSsForBootloaderInstallation:
            #For each OS that needs the new bootloader installed, grab the partition, and the package manager.
            Partition = OS.split()[-5]
            PackageManager = OS.split()[-1]

            logger.info("BootloaderInstallationTools: Main().InstallNewBootloader(): Preparing to install the new bootloader "+BootloaderToInstall+" in OS: "+OS+"...")
            wx.CallAfter(ParentWindow.UpdateOutputBox, "\n###Preparing to install the new bootloader in OS: "+OS+"...###\n") #*** Show the new bootloader here ***
            wx.CallAfter(ParentWindow.UpdateCurrentOpText, Message="Preparing to install the new bootloader(s)...")

            #Grab the architecture.
            Arch = OS.split()[-8]
            if Arch == "64-bit":
                Arch = "x86_64"

            else:
                Arch = "i686"

            #If we're not on a live disk, and the partition is AutoRootFS, let the installer function know that we aren't using chroot.
            if LiveDisk == False and Partition == AutoRootFS:
                #Update the package lists.
                retval = BootloaderInstallationTools().UpdatePackageLists(PackageManager=PackageManager, UseChroot=False)

                wx.CallAfter(ParentWindow.UpdateCurrentOpText, Message="Installing the new bootloader(s)...")
                wx.CallAfter(ParentWindow.UpdateCurrentProgress, 55)       
                wx.CallAfter(ParentWindow.UpdateOutputBox, "\n###Installing the new bootloader in OS: "+OS+"...###\n")

                if BootloaderToInstall == "GRUB2":
                    retval = BootloaderInstallationTools().InstallGRUB2(PackageManager=PackageManager, UseChroot=False, Arch=Arch)

                elif BootloaderToInstall == "LILO":
                    retval = BootloaderInstallationTools().InstallLILO(PackageManager=PackageManager, UseChroot=False, Arch=Arch)

                elif BootloaderToInstall == "GRUB-UEFI":
                    #Mount the UEFI partition at /boot/efi.
                    #Unmount it first though, in case it's already mounted. *** Is this necessary? Check if it's mounted first! ***
                    CoreTools().Unmount(UEFISystemPartition) #*** Check it worked! ***
                    CoreTools().MountPartition(Partition=UEFISystemPartition, MountPoint="/boot/efi") #*** Check this worked! ***

                    retval = BootloaderInstallationTools().InstallGRUBUEFI(PackageManager=PackageManager, UseChroot=False, Arch=Arch)

                elif BootloaderToInstall == "ELILO":
                    #Unmount the UEFI Partition now.
                    CoreTools().Unmount(UEFISystemPartition) #*** Check it worked! ***

                    retval = BootloaderInstallationTools().InstallELILO(PackageManager=PackageManager, UseChroot=False, Arch=Arch)

            #Otherwise, setup the chroot and everything else first, and tell it we are using chroot, and pass the mountpoint to it.
            else:
                #Mount the partition using the global mount function.
                MountPoint = "/mnt"+Partition
                Retval = CoreTools().MountPartition(Partition=Partition, MountPoint=MountPoint)

                if Retval != 0:
                    logger.error("BootloaderInstallationTools: Main().InstallNewBootloader(): Failed to remount "+Partition+"! Warn the user and skip this OS.")
                    DialogTools().ShowMsgDlg(Kind="error", Message="WxFixBoot failed to mount the partition containing: "+OS+"! Bootloader installation cannot continue! This may leave your system, or this OS, in an unbootable state. It is recommended to do a Bad Sector check, and then try again.")

                else:
                    #Set up chroot.
                    CoreBackendTools().SetUpChroot(MountPoint=MountPoint)

                    #If there's a seperate /boot partition for this OS, make sure it's mounted.
                    CoreBackendTools().StartThreadProcess(['chroot', MountPoint, 'mount', '-av'], ShowOutput=False) #*** Read this OS's FSTAB instead of hoping that this works, cos then we can use the global mount function to do this ***

                    #Update the package lists.
                    retval = BootloaderInstallationTools().UpdatePackageLists(PackageManager=PackageManager, UseChroot=True, MountPoint=MountPoint)

                    wx.CallAfter(ParentWindow.UpdateCurrentOpText, Message="Installing the new bootloader(s)...")
                    wx.CallAfter(ParentWindow.UpdateCurrentProgress, 55)       
                    wx.CallAfter(ParentWindow.UpdateOutputBox, "\n###Installing the new bootloader in OS: "+OS+"...###\n")

                    #Install the bootloader.
                    if BootloaderToInstall == "GRUB2":
                        retval = BootloaderInstallationTools().InstallGRUB2(PackageManager=PackageManager, UseChroot=True, MountPoint=MountPoint, Arch=Arch)

                    elif BootloaderToInstall == "LILO":
                        retval = BootloaderInstallationTools().InstallLILO(PackageManager=PackageManager, UseChroot=True, MountPoint=MountPoint, Arch=Arch)

                    elif BootloaderToInstall == "GRUB-UEFI":
                        #Mount the UEFI partition at MountPoint/boot/efi.
                        #Unmount it first though, in case it's already mounted. *** Alternately check where it's mounted and leave it if it's okay ***
                        CoreTools().Unmount(UEFISystemPartition) #*** Check it worked! ***
                        CoreTools().MountPartition(Partition=UEFISystemPartition, MountPoint=MountPoint+"/boot/efi") #*** Check it worked! ***
                        retval = BootloaderInstallationTools().InstallGRUBUEFI(PackageManager=PackageManager, UseChroot=True, MountPoint=MountPoint, Arch=Arch)

                    elif BootloaderToInstall == "ELILO":
                        #Unmount the UEFI Partition now, and update the mtab inside chroot.
                        CoreTools().Unmount(UEFISystemPartition) #*** Check it worked! ***
                        CoreBackendTools().UpdateChrootMtab(MountPoint=MountPoint)

                        retval = BootloaderInstallationTools().InstallELILO(PackageManager=PackageManager, UseChroot=True, MountPoint=MountPoint, Arch=Arch)

                    #If there's a seperate /boot partition for this OS, make sure it's unmounted before removing the chroot.
                    CoreTools().Unmount(MountPoint+"/boot") #*** Check it worked *** *** Test that this works ***
                    CoreBackendTools().UpdateChrootMtab(MountPoint=MountPoint)

                    #Tear down chroot.
                    CoreBackendTools().TearDownChroot(MountPoint=MountPoint)

            if retval != 0:
                #Something went wrong! Log it and notify the user.
                BootloaderInstallSucceded = False
                logger.error("BootloaderInstallationTools: Main().InstallNewBootloader(): Failed to install "+BootloaderToInstall+" in OS: "+OS+"! This may mean the system (or this OS) is now unbootable! We'll continue anyway. Warn the user.")
                DialogTools().ShowMsgDlg(Kind="error", Message="WxFixBoot failed to install "+BootloaderToInstall+" in: "+OS+"! This may leave this OS, or your system, in an unbootable state. It is recommended to do a Bad Sector check, unplug any non-essential devices, and then try again.") #*** Maybe ask to try again right now ***

            wx.CallAfter(ParentWindow.UpdateOutputBox, "\n###Finished installing the new bootloader in OS: "+OS+"...###\n") #*** Show the name of the new bootloader here ***

        #Log and notify the user that we're finished removing bootloaders.
        logger.info("BootloaderInstallationTools: Main().InstallNewBootloader(): Finished Installing bootloaders...")
        wx.CallAfter(ParentWindow.UpdateCurrentOpText, Message="Finished Installing bootloaders...")
        wx.CallAfter(ParentWindow.UpdateCurrentProgress, 75)
        return BootloaderInstallSucceded #*** Keep the results for each OS here, and note which one(s) failed! ***

#End main Class.
