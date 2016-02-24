#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Main Startup Tools in the StartupTools Package for WxFixBoot Version 1.1~pre1
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
    def CheckDepends(self):
        """Check dependencies, and show an error message and kill the app if the dependencies are not met."""
        #Create a temporary list to allow WxFixBoot to notify the user of particular unmet dependencies. *** Remove parted soon *** *** Maybe remove lsblk later ***
        CmdList = ("mount", "parted", "lsb_release", "dmidecode", "lsblk", "chroot", "dd")

        #Create a list to contain names of failed commands.
        FailedList = []

        for Command in CmdList:
            #Run the command with its argument and log the output (if in debug mode)
            Retval, Output = CoreTools().StartProcess("which "+Command, ReturnOutput=True)

            if Retval != 0:
                logger.error("MainStartupTools: Main().CheckDepends(): Dependency problems! Command: "+Command+" failed to execute or wasn't found.")
                logger.error("MainStartupTools: Main().CheckDepends(): The error was: "+Output)
                FailedList.append(Command)

        #Check if any commands failed.
        if FailedList != []:
            #Missing dependencies!
            logger.critical("MainStartupTools: Main().CheckDepends(): Dependencies missing! WxFixBoot will exit. The missing dependencies are: "+', '.join(FailedList)+". Exiting.")
            DialogTools().ShowMsgDlg(Kind="error", Message="The following dependencies could not be found on your system: "+', '.join(FailedList)+".\n\nPlease install the missing dependencies. WxFixBoot will now exit.")

            wx.Exit()
            sys.exit("Missing dependencies: "+', '.join(FailedList)+" Exiting...")

    def UnmountAllFS(self):
        """Unmount any unnecessary filesystems, to prevent data corruption."""
        #Warn about removing devices. *** Clarify this message ***
        DialogTools().ShowMsgDlg(Kind="info", Message="Unnecessary filesystems will now be unmounted. Please remove all unneeded devices connected to your computer and close any other running programs, then click okay. *** This won't apply anymore when changing device info gatherer *** If you're doing a disk check, please plug in any devices you wish to check. However, if you are doing other operations, please do them seperately.")

        #Attempt unmount of all filesystems.
        CoreTools().StartProcess("umount -ad") #*** Check it worked! ***

        #Make sure that we still have rw access on live disks.
        CoreTools().RemountPartition("/") #*** Check it worked! ***

    def CheckFS(self):
        """Check all unmounted filesystems."""
        CoreTools().StartProcess("fsck -ARMp") #*** Check it worked! ***

    def MountCoreFS(self):
        """Mount all core filsystems defined in the /etc/fstab of the current operating system."""
        CoreTools().StartProcess("mount -avw") #*** Check it worked! ***

    def DetectDevicesPartitionsAndPartSchemes(self):
        """Detect all devices, partitions, and their partition schemes.""" #*** This will need serious work as I change the way wxfixboot handles disks with dictionaries and stuff ***
        #*** A fair bit of this info can be gathered using DDRescue-GUI's getdevinfo package ***
        #Create a list for the devices.
        DeviceList = []

        #Create a list for Partition Schemes.
        AutoPartSchemeList = []

        #Create a list for the partitions.
        PartitionListWithFSType = []

        OutputList = CoreTools().StartProcess("lsblk -r -o NAME,FSTYPE", ReturnOutput=True)[1].replace("NAME FSTYPE\n", "").split()

        #Populate the device list, and the Partition List including FS Type.
        for Disk in OutputList:
            #Check if the disk is a hard drive, and doesn't end with a digit (isn't a partition).
            if Disk[0:2] in ('sd', 'hd') and Disk[-1].isdigit() == False:

                #First AutoPartSchemeList
                try:
                    #Check if the disk is already in DeviceList, as if it is, it won't be duplicated in AutoPartSchemeList either this way.
                    DeviceList.index("/dev/"+Disk)

                except ValueError:
                    #It isn't, add it.
                    PartScheme = CoreStartupTools().GetDevPartScheme("/dev/"+Disk)
                    AutoPartSchemeList.append(PartScheme)

                #Now DeviceList
                try:
                    #Check if the disk is already in DeviceList.
                    DeviceList.index(Disk)

                except ValueError:
                    #It isn't, add it.
                    DeviceList.append("/dev/"+Disk)

            #If instead the partition is a partition on a hard drive, add it to the Partition List with FSType, along with the next disk, if it is not a device or partition.
            elif Disk[0:2] in ('sd', 'hd') and Disk[-1].isdigit() == True:
                PartitionListWithFSType.append("/dev/"+Disk)
                Temp = OutputList[OutputList.index(Disk)+1]

                #Add the next element if it's an FSType. If it isn't, put "Unknown" in its place.
                if Temp[0:2] not in ('sd', 'hd'):
                    PartitionListWithFSType.append(Temp)

                else:
                    PartitionListWithFSType.append("Unknown")

        #Now set PartSchemeList the same as AutoPartSchemeList.
        PartSchemeList = AutoPartSchemeList[:]

        logger.debug("MainStartupTools: Main().DetectDevicesPartitionsAndPartSchemes(): DeviceList, PartitionListWithFSType and PartSchemeList Populated okay. Contents (respectively): "+', '.join(DeviceList)+" and: "+', '.join(PartitionListWithFSType)+" and: "+', '.join(PartSchemeList))

        #Finally, save two variables showing whether there are any mbr or gpt entries on the disks. *** This will almost definitely be unneeded. Is this even helpful? ***
        #GPT
        try:
            PartSchemeList.index("gpt")

        except ValueError:
            GPTInAutoPartSchemeList = False

        else:
            GPTInAutoPartSchemeList = True

        #MBR(MSDOS)
        try:
            PartSchemeList.index("msdos")

        except ValueError:
            MBRInAutoPartSchemeList = False

        else:
            MBRInAutoPartSchemeList = True

        return PartitionListWithFSType, DeviceList, PartSchemeList, AutoPartSchemeList, GPTInAutoPartSchemeList, MBRInAutoPartSchemeList

    def DetectLinuxPartitions(self):
        """Get a list of partitions of type ext (1,2,3 or 4) / btrfs / xfs / jfs / zfs / minix / reiserfs."""
        #*** A fair bit of this info can be gathered using DDRescue-GUI's getdevinfo package ***
        LinuxPartList = []

        #Run the command to find them, and save the results in a list.
        TempList = CoreTools().StartProcess("lsblk -r -o NAME,FSTYPE", ReturnOutput=True)[1].split("\n")

        OutputList = []

        for Line in TempList:
            if ("ext" or "btrfs" or "xfs" or "jfs" or "zfs" or "minix" or "reiserfs") in Line:
                OutputList.append(Line.split()[0])
                OutputList.append(Line.split()[1])

        #Create a list of only the partitions in the list.
        for Partition in OutputList:
            if Partition[0:2] in ('sd', 'hd') and Partition[-1].isdigit():
                LinuxPartList.append("/dev/"+Partition)

        #Check if there are any linux partitions in the list.
        if LinuxPartList == []:
            #There are none, exit. *** Clarify this message ***
            logger.critical("MainStartupTools: Main().DetectLinuxPartitions(): No Linux Partitions (on HDD) of type ext(1,2,3,4), btrfs, xfs, jfs, zfs, minix or resierfs found! Exiting...")
            DialogTools().ShowMsgDlg(Kind="error", Message="You don't appear to have any Linux partitions on your hard disks. If you do have Linux partitions but WxFixBoot hasn't found them, please file a bug or ask a question on WxFixBoot's launchpad page. If you're using Windows or Mac OS X, then sorry as WxFixBoot has no support for these operating systems. You could instead use the tools provided by Microsoft and Apple to fix any issues with your computer. WxFixBoot will now exit.")

            #Exit. *** Can we do this from here? Maybe call the parent. Until I fix this the GUI will crash if this happens! ***
            wx.Exit()
            sys.exit("Critical Error! No supported Linux filesystems (on HDD) found. Will now exit...")

        logger.debug("MainStartupTools: Main().DetectLinuxPartitions(): LinuxPartList Populated okay. Contents: "+', '.join(LinuxPartList))
        return LinuxPartList

    def GetRootFSandRootDev(self, LinuxPartList):
        """Determine RootFS, and RootDevice"""
        #*** This should be done for each OS installed and stored that way, preventing unwanted config and damaged bootloaders. Major work needed here. *** *** Maybe add more logging messages ***
        Result = DialogTools().ShowYesNoDlg(Message="Is WxFixBoot being run on live media, such as an Ubuntu Installer Disk, or Parted Magic?", Title="WxFixBoot - Live Disk?")
        
        if Result:
            logger.warning("MainStartupTools: Main().GetRootFSandRootDev(): User reported WxFixBoot is on a live disk...")

            #Make an early call to GetLinuxOSs()
            LiveDisk = True
            OSList, DefaultOS, AutoDefaultOS = self.GetLinuxOSs(LinuxPartList, LiveDisk, "")

            Result = DialogTools().ShowChoiceDlg(Message="Please select the Linux Operating System you normally boot.", Title="WxFixBoot - Select Operating System", Choices=OSList) #*** This can be removed when I change/remove this function ***

            #Save the info.
            logger.info("MainStartupTools: Main().GetRootFSandRootDev(): User selected default Linux OS of: "+Result+". Continuing...")
            DefaultOS = Result
            AutoDefaultOS = DefaultOS
            RootFS = Result.split()[-1]
            AutoRootFS = RootFS
            RootDevice = RootFS[0:8]
            AutoRootDevice = RootDevice

        else:
            logger.warning("MainStartupTools: Main().GetRootFSandRootDev(): User reported WxFixBoot isn't on a live disk...")

            DialogTools().ShowMsgDlg(Kind="info", Message="Your current OS will be taken as the default OS. You can reset this later if you wish.")

            #By the way the default OS in this case is set later, when OS detection takes place. *** Maybe get rid of this try statement when I change/remove this *** *** Badly written, what if we get a UUID? Use the heirachy when I switch ***
            try:
                RootFS = CoreTools().StartProcess("mount", ReturnOutput=True)[1].split()[0] #*** Change this later ***
                AutoRootFS = RootFS
                RootDevice = RootFS[0:8]
                AutoRootDevice = RootDevice
                LiveDisk = False
                DefaultOS = ""
                AutoDefaultOS = DefaultOS
                OSList = []

            except IndexError:
                logger.critical("MainStartupTools: Main().GetRootFSandRootDev(): Couldn't determine the root device! This program cannot safely continue. WxFixBoot will now exit, and warn the user...")
                DialogTools().ShowMsgDlg(Kind="error", Message="WxFixBoot couldn't determine your root device (the device the current OS is running on)! The most likely reason for this is that you're running from a live disk and misreported it, so try restarting WxFixBoot and making the other choice. WxFixBoot will now exit.")
                wx.Exit() #*** Can we do this from here? Maybe call the parent. Until I fix this the GUI will crash if this happens! ***
                sys.exit("CRITICAL ERROR! Couldn't determine the root device! This program cannot safely continue. Exiting...")

        return AutoRootFS, RootFS, AutoRootDevice, RootDevice, LiveDisk, AutoDefaultOS, DefaultOS, OSList

    def GetLinuxOSs(self, LinuxPartList, LiveDisk, AutoRootFS):
        """Get the names of all Linux OSs on the HDDs."""
        #*** This will need changing, but will not need too much work to adapt it to using dictionaries ***
        #*** Crashes at log line in __init__() if we couldn't detect the current OS ***
        logger.debug("MainStartupTools: Main().GetLinuxOSs(): Finding Linux operating systems...")
        OSList = []
        DefaultOS = ""
        AutoDefaultOS = DefaultOS

        #Get Linux OSs.
        for Partition in LinuxPartList:
            logger.debug("MainStartupTools: Main().GetLinuxOSs(): Looking on "+Partition+"...")

            #Skip some stuff if we're not on a live disk and Partition == AutoRootFS.
            if LiveDisk == False and Partition == AutoRootFS:
                #Look for an OS on this partition.
                Retval, Temp = CoreTools().StartProcess("lsb_release -sd", ReturnOutput=True)
                OSName = Temp.replace('\n', '')

                #Run the function to get the architechure, letting the function know that it shouldn't use chroot.
                OSArch = CoreStartupTools().DetermineOSArchitecture(Partition=Partition, Chroot=False)

                #If the OS's name wasn't found, but its architecture was, there must be an OS here, so ask the user for its name.
                if Retval != 0 and OSArch != None:
                    #As this is the current OS, force the user to name it, or be stuck permanently in a loop.
                    OSName = None
                    while OSName == None:
                        OSName = CoreStartupTools().AskForOSName(Partition=Partition, OSArch=OSArch, AutoRootFS=AutoRootFS)

                #If we found all of the information, add the OS to the list.
                if OSName != "" and OSArch != None:
                    #Add this information to the OSList, and set it as the default OS
                    DefaultOS = OSName+' (Current OS) '+OSArch+' on partition '+Partition
                    AutoDefaultOS = DefaultOS
                    OSList.append(OSName+' (Current OS) '+OSArch+' on partition '+Partition)

            elif Partition[0:7] in ('/dev/sd', '/dev/hd'):
                #We're interested in this partition, because it's an HDD or usb disk partition.
                #Mount the partition.
                Retval = CoreTools().MountPartition(Partition=Partition, MountPoint="/mnt"+Partition)

                #Check if anything went wrong.
                if Retval != 0:
                    #Ignore the partition.
                    logger.warning("MainStartupTools: Main().GetLinuxOSs(): Couldn't mount "+Partition+"! Skipping this partition...")

                else:
                    #Look for an OS on this partition.
                    Retval, Temp = CoreTools().StartProcess("chroot /mnt"+Partition+" lsb_release -sd", ReturnOutput=True)
                    OSName = Temp.replace('\n', '')

                    #Run the function to get the architechure, letting the function know that it shouldn't use chroot.
                    OSArch = CoreStartupTools().DetermineOSArchitecture(Partition=Partition, Chroot=True)

                    #If the OS's name wasn't found, but its architecture was, there must be an OS here, so ask the user for its name.
                    if Retval != 0 and OSArch != None:
                        OSName = CoreStartupTools().AskForOSName(Partition=Partition, OSArch=OSArch, AutoRootFS=AutoRootFS)

                    #Don't use elif here, so we'll also save it if CoreStartupTools().AskForOSName was used to determine the name. If it is still None, the user skipped naming it. Ignore it instead and skip the rest of the loop. *** I don't understand this, so check back later ***
                    if OSName != None and OSArch != None:
                        #Add this information to the OSList.
                        OSList.append(OSName+' '+OSArch+' on partition '+Partition)

                #Unmount the filesystem.
                Retval = CoreTools().Unmount("/mnt"+Partition) #*** Check the return value so we can take action if this doesn't work! Otherwise we may delete data from a drive! Mind, it looks like rm won't let you fortunately. ***

                #Remove the temporary mountpoint
                os.rmdir("/mnt"+Partition)

        #Check that at least one Linux OS was detected.
        if len(OSList) >= 1:
            logger.debug("MainStartupTools: Main().GetLinuxOSs(): Done, OSList Populated okay. Contents: "+', '.join(OSList))
            return OSList, DefaultOS, AutoDefaultOS

        else:
            logger.critical("MainStartupTools: Main().GetLinuxOSs(): Couldn't find any linux operating systems! Linux partitions were detected, but don't appear to contain any OSs! WxFixBoot will now exit, and warn the user...")
            DialogTools().ShowMsgDlg(Kind="error", Message="Linux partitions were found on your computer, but no Linux operating systems were found! Perhaps you need to recover data from your hard drive, or restore an image first? If you're using Parted Magic, you'll have access to tools that can do that for you now. Otherwise, you may need to install them. WxFixBoot will now exit.")
            wx.Exit() #*** Can we do this from here? Maybe call the parent. Until I fix this the GUI will crash if this happens! ***
            sys.exit("CRITICAL ERROR! Couldn't find any linux operating systems! Linux partitions were detected, but don't appear to contain any OSs! Exiting...")

    def GetFirmwareType(self):
        """Get the firmware type"""
        #Check if the firmware type is UEFI.
        Output = CoreTools().StartProcess("dmidecode -q -t BIOS", ReturnOutput=True)[1]

        if "UEFI" not in Output:
            #It's BIOS.
            logger.info("MainStartupTools: Main().GetFirmwareType(): Detected Firmware Type as BIOS...")
            FirmwareType = "BIOS"
            AutoFirmwareType = "BIOS"
            UEFIVariables = False

        else:
            #It's UEFI.
            logger.info("MainStartupTools: Main().GetFirmwareType(): Detected Firmware Type as UEFI. Looking for UEFI Variables...")
            FirmwareType = "UEFI"
            AutoFirmwareType = "UEFI"

            #Also, look for UEFI variables.
            #Make sure efivars module is loaded. If it doesn't exist, continue anyway.
            CoreTools().StartProcess("modprobe efivars")

            #Look for the UEFI vars in some common directories. *** Just because the dir is there doesn't mean the vars are (I think) ***
            if os.path.isdir("/sys/firmware/efi/vars"):
                UEFIVariables = True
                logger.info("MainStartupTools: Main().GetFirmwareType(): Found UEFI Variables at /sys/firmware/efi/vars...")

            elif os.path.isdir("/sys/firmware/efi/efivars"):  
                UEFIVariables = True
                logger.info("MainStartupTools: Main().GetFirmwareType(): Found UEFI Variables at /sys/firmware/efi/efivars...")

            else:
                logger.warning("MainStartupTools: Main().GetFirmwareType(): UEFI vars not found in /sys/firmware/efi/vars or /sys/firmware/efi/efivars. Attempting manual mount...")

                #Attempt to manually mount the efi vars, as we couldn't find them.
                if not os.path.isdir("/sys/firmware/efi/vars"):
                    os.mkdir("/sys/firmware/efi/vars")

                Stdout = CoreTools().StartProcess("mount -t efivarfs efivars /sys/firmware/efi/vars").replace('\n', '') #*** If we can, use the new universal mount function to do this ***

                if Stdout != "None":
                    logger.warning("MainStartupTools: Main().GetFirmwareType(): Failed to mount UEFI vars! Warning user. Ignoring and continuing.")

                    #UEFI vars not available or couldn't be mounted.
                    DialogTools().ShowMsgDlg(Kind="warning", Message="Your computer uses UEFI firmware, but the UEFI variables couldn't be mounted or weren't found. Please ensure you've booted in UEFI mode rather than legacy mode to enable access to the UEFI variables. You can attempt installing a UEFI bootloader without them, but it might not work, and it isn't recommended.")
                    UEFIVariables = False

                else:
                    #Successfully mounted them.
                    UEFIVariables = True
                    logger.info("MainStartupTools: Main().GetFirmwareType(): Mounted UEFI Variables at: /sys/firmware/efi/vars. Continuing...")

        return FirmwareType, AutoFirmwareType, UEFIVariables

    def GetBootloader(self, RootDevice, LiveDisk, FirmwareType):
        """Determine the current bootloader."""
        #*** Do some of this for each OS *** *** Will need a LOT of modification when I switch to dictionaries ***
        logger.debug("MainStartupTools: Main().GetBootloader(): Trying to determine bootloader...")

        #Run some inital scripts
        logger.debug("MainStartupTools: Main().GetBootloader(): Copying MBR bootsector to /tmp/wxfixboot/mbrbootsect...")
        CoreTools().StartProcess("dd if="+RootDevice+" bs=512 count=1 > /tmp/wxfixboot/mbrbootsect") #*** See if we can save it to memory instead *** *** We probably need to do this for each and every device with a partition containing an OS, as the rootdevice principle falls apart here ***

        #Wrap this in a loop, so once a Bootloader is found, searching can stop.
        while True:
            #Check for a UEFI partition.
            #Check for a UEFI system partition.
            logger.debug("MainStartupTools: Main().GetBootloader(): Checking For a UEFI partition...")
            AutoUEFISystemPartition, FatPartitions = CoreStartupTools().CheckForUEFIPartition(LiveDisk)
            UEFISystemPartition = AutoUEFISystemPartition

            #If there is no UEFI partition, ask the user.
            if UEFISystemPartition == "None":
                #There is no UEFI partition.
                HelpfulUEFIPartition = False

                #Look for BIOS bootloaders here.
                #Check for GRUB in the MBR
                logger.debug("MainStartupTools: Main().GetBootloader(): Checking for GRUB in bootsector...")
                if CoreStartupTools().CheckForGRUBBIOS():
                    #We have GRUB BIOS, now figure out which version we have!
                    AutoBootloader = CoreStartupTools().DetermineGRUBBIOSVersion(LiveDisk=LiveDisk)
                    break

                #Check for LILO in MBR
                logger.debug("MainStartupTools: Main().GetBootloader(): Checking for LILO in bootsector...")
                if CoreStartupTools().CheckForLILO():
                    #We have LILO!
                    AutoBootloader = "LILO"
                    logger.info("MainStartupTools: Main().GetBootloader(): Found LILO in MBR (shown as LILO in GUI. Continuing...")
                    break

                #No bootloader was found, so ask the user instead.
                #Do a manual selection of the bootloader.
                logger.warning("MainStartupTools: Main().GetBootloader(): Asking user what the bootloader is, as neither GRUB nor LILO was detected in MBR, and no UEFI partition was found...")
                AutoBootloader = CoreStartupTools().ManualBootloaderSelect(UEFISystemPartition=UEFISystemPartition, FirmwareType=FirmwareType)
                break

            #Mount (or skip if mounted) the UEFI partition.
            logger.info("MainStartupTools: Main().GetBootloader(): Attempting to mount the UEFI partition (if it isn't already)...")
            UEFISYSPMountPoint = CoreStartupTools().MountUEFIPartition(UEFISystemPartition)
            logger.info("MainStartupTools: Main().GetBootloader(): UEFI Partition mounted at: "+UEFISYSPMountPoint+". Continuing to look for UEFI bootloaders...")

            #Attempt to figure out which bootloader is present.
            #Check for GRUB-UEFI.
            logger.debug("MainStartupTools: Main().GetBootloader(): Checking for GRUB-UEFI in UEFI Partition...")
            GrubEFI, HelpfulUEFIPartition = CoreStartupTools().CheckForGRUBUEFI(UEFISYSPMountPoint)

            if GrubEFI:
                #We have GRUB-UEFI!
                AutoBootloader = "GRUB-UEFI"
                logger.info("MainStartupTools: Main().GetBootloader(): Found GRUB-UEFI in UEFI Partition (shown as GRUB-UEFI in GUI). Continuing...")
                break

            #Check for ELILO
            logger.debug("MainStartupTools: Main().GetBootloader(): Checking for ELILO in UEFI Partition...")
            ELILO, HelpfulUEFIPartition = CoreStartupTools().CheckForELILO(UEFISYSPMountPoint)

            if ELILO:
                #We have ELILO!
                AutoBootloader = "ELILO"
                logger.info("MainStartupTools: Main().GetBootloader(): Found ELILO in UEFI Partition (shown as ELILO in GUI). Continuing...")
                break

            #Obviously, no bootloader has been found.
            #Do a manual selection.
            logger.warning("MainStartupTools: Main().GetBootloader(): Asking user what the bootloader is, as no bootloader was found...")
            AutoBootloader = CoreStartupTools().ManualBootloaderSelect(UEFISystemPartition=UEFISystemPartition, FirmwareType=FirmwareType)

            #The program waits until something was chosen, so if it executes this, the bootloader has been set.
            break

        #Set the default bootloader value.
        Bootloader = AutoBootloader

        return Bootloader, AutoBootloader, AutoUEFISystemPartition, UEFISystemPartition, HelpfulUEFIPartition, FatPartitions

    def SetDefaults(self):
        """Set Default for some variables"""
        #Options in MainWindow
        ReinstallBootloader = False
        UpdateBootloader = False 
        QuickFSCheck = False
        BadSectCheck = False

        #Options in Optionsdlg1
        #Set them up for default settings.
        SaveOutput = True
        FullVerbose = False
        Verify = True
        BackupBootSector = False
        BackupPartitionTable = False
        MakeSystemSummary = True
        BootloaderTimeout = -1 #Don't change the timeout by default.

        #Options in Bootloader Options dlg
        BootloaderToInstall = "None"
        BLOptsDlgRun = False

        #Options in Restore dlgs
        RestoreBootSector = False
        BootSectorFile = "None"
        BootSectorTargetDevice = "None"
        BootSectorBackupType = "None"
        RestorePartitionTable = False
        PartitionTableFile = "None"
        PartitionTableTargetDevice = "None"
        PartitionTableBackupType = "None"

        #Other Options
        OptionsDlg1Run = False

        return ReinstallBootloader, UpdateBootloader, QuickFSCheck, BadSectCheck, SaveOutput, FullVerbose, Verify, BackupBootSector, BackupPartitionTable, MakeSystemSummary, BootloaderTimeout, BootloaderToInstall, BLOptsDlgRun, RestoreBootSector, BootSectorFile, BootSectorTargetDevice, BootSectorBackupType, RestorePartitionTable, PartitionTableFile, PartitionTableTargetDevice, PartitionTableBackupType, OptionsDlg1Run

    def FinalCheck(self, LiveDisk, PartitionListWithFSType, LinuxPartList, DeviceList, AutoRootFS, RootFS, AutoRootDevice, RootDevice, DefaultOS, AutoDefaultOS, OSList, FirmwareType, AutoFirmwareType, UEFIVariables, PartSchemeList, AutoPartSchemeList, GPTInAutoPartSchemeList, MBRInAutoPartSchemeList, Bootloader, AutoBootloader, UEFISystemPartition, HelpfulUEFIPartition): #*** This is where I am in optimising these functions, and I will do this later *** *** This is a real mess! ***
        """Check for any conflicting options, and that each variable is set."""
        #Create a temporary list containing all variables to be checked, and a list to contain failed variables.
        VarList = ('LiveDisk', 'PartitionListWithFSType', 'LinuxPartList', 'DeviceList', 'AutoRootFS', 'RootFS', 'AutoRootDevice', 'RootDevice', 'DefaultOS', 'AutoDefaultOS', 'OSList', 'FirmwareType', 'AutoFirmwareType', 'UEFIVariables', 'PartSchemeList', 'AutoPartSchemeList', 'GPTInAutoPartSchemeList', 'MBRInAutoPartSchemeList', 'Bootloader', 'AutoBootloader', 'UEFISystemPartition', 'HelpfulUEFIPartition')
        FailedList = []

        #Check each global variable (visible to this function as local) is set and declared.
        for var in VarList:
            if var in locals():
                if var == None:
                    #It isn't set.                    
                    logger.critical("MainStartupTools: Main().FinalCheck(): Variable "+var+" hasn't been set, adding it to the failed list...")
                    FailedList.append(var)

            else:
                #It isn't declared.                    
                logger.critical("MainStartupTools: Main().FinalCheck(): Variable "+var+" hasn't been declared, adding it to the failed list...")
                FailedList.append(var)

        #Check if any variables weren't set.
        if FailedList != []:
            #Missing dependencies!
            logger.critical("MainStartupTools: Main().FinalCheck(): Required Settings: "+', '.join(FailedList)+" have not been Determined! This is probably a bug in the program! Exiting...")
            DialogTools().ShowMsgDlg(Kind="error", Message="The required variables: "+', '.join(FailedList)+", have not been set! WxFixBoot will now shut down to prevent damage to your system. This is probably a bug in the program. Check the log file at /tmp/wxfixboot.log")

            wx.Exit() #*** Can we do this from here? Maybe call the parent. Until I fix this the GUI will crash if this happens! ***
            sys.exit("WxFixBoot: Critial Error: Incorrectly set settings:"+', '.join(FailedList)+" Exiting...")

        #Check and warn about conflicting settings. *** These aren't helpful to people who are new and just want to fix it quick. Maybe try to clarify them/automatically deal with this stuff? Perhaps avoid some of these situations completely by improving startup code ***
        #Firmware type warnings.
        if FirmwareType == "BIOS" and Bootloader in ('GRUB-UEFI', 'ELILO'):
            logger.warning("MainStartupTools: Main().FinalCheck(): Bootloader is UEFI-type, but system firmware is BIOS! Odd, perhaps a migrated drive? Continuing and setting firmware type to UEFI...")
            DialogTools().ShowMsgDlg(Kind="warning", Message="Your computer seems to use BIOS firmware, but you're using a UEFI-enabled bootloader! WxFixBoot reckons your firmware type was misdetected, and will now set it to UEFI. BIOS firmware does not support booting UEFI-enabled bootloaders, so if you think your firmware type actually is BIOS, it is recommended to install a BIOS-enabled bootloader instead, such as GRUB2. You can safely ignore this message if your firmware type is UEFI.")
            AutoFirmwareType = "UEFI"
            FirmwareType = "UEFI"

        if FirmwareType == "BIOS" and GPTInAutoPartSchemeList == True:
            logger.warning("MainStartupTools: Main().FinalCheck(): Firmware is BIOS, but at least one device on the system is using a gpt partition table! This device probably won't be bootable. WxFixBoot suggests repartitioning, if you intend to boot from that device.")
            DialogTools().ShowMsgDlg(Kind="warning", Message="Your computer uses BIOS firmware, but you're using an incompatable partition system on at least one device! BIOS firmware will probably fail to boot your operating system, if it resides on that device, so a repartition may be necessary for that device. You can safely ignore this message if your firmware type has been misdetected, or if you aren't booting from that device.")

        #Partition scheme warnings.
        if MBRInAutoPartSchemeList == True and Bootloader in ('GRUB-UEFI', 'ELILO'):
            logger.warning("MainStartupTools: Main().FinalCheck(): MBR partition table on at least one device, and a UEFI bootloader is in use! This might not work properly. WxFixBoot suggests repartitioning.")
            DialogTools().ShowMsgDlg(Kind="warning", Message="You're using a UEFI-enabled bootloader, but you're using an incompatable partition system on at least one device! Some firmware might not support this setup, especially if the UEFI system partition resides on this device, so it is recommended to repartition the device. Ignore this message if you do not boot from this device.")

        if GPTInAutoPartSchemeList == True and Bootloader in ('GRUB2', 'LILO', 'GRUB-LEGACY'):
            logger.warning("MainStartupTools: Main().FinalCheck(): GPT Partition table on at least one device with msdos bootloader! Most BIOS firmware cannot read GPT disks. WxFixBoot suggests repartitioning.")
            DialogTools().ShowMsgDlg(Kind="warning", Message="You're using a BIOS-enabled bootloader, but you're using an incompatable partition system on at least one device! Most firmware will not support this setup. Ignore this message if you do not boot from this device.")

        #Bootloader warnings.
        if HelpfulUEFIPartition == False and UEFISystemPartition != "None":
            logger.warning("MainStartupTools: Main().FinalCheck(): Empty UEFI partition!")
            DialogTools().ShowMsgDlg(Kind="warning", Message="Your UEFI system partition is empty or doesn't contain any detected bootloaders. If you just created your UEFI system partition, please ensure it's formatted as fat32 or fat16 (Known as vfat in Linux), and then you may continue to install a UEFI bootloader on it. If WxFixBoot didn't detect your UEFI-enabled bootloader, it's still safe to perform operations on the bootloader.")

        return AutoFirmwareType, FirmwareType

#End main Class.
