#added pxe_lego driver
#changed in /etc/ironic/ironic.conf : enabled_drivers = pxe_lego

#how to add a node:

driver="pxe_lego"
MAC="05:0c:29:71:ef:b3"
lego_ev3_ip="10.0.1.1"
lego_ev3_port="A"
pxe_deploy_kernel="0196a3f1-442a-424e-9eff-eed0b29cfccf"
pxe_deploy_ramdisk="bf0c72f3-e3a1-4583-baae-c5fded0d6278"
CHASSIS_ID="54666f86-f453-4b9a-991a-7f0a31ed3eeb"
IRONIC_VM_SPECS_CPU="1"
IRONIC_VM_SPECS_RAM="1024"
IRONIC_VM_SPECS_DISK="10"

NODE=$(ironic node-create --chassis_uuid $CHASSIS_ID -d $driver -i lego_ev3_address=$lego_ev3_ip -i lego_ev3_port=$lego_ev3_port -p cpus=$IRONIC_VM_SPECS_CPU -p memory_mb=$IRONIC_VM_SPECS_RAM -p local_gb=$IRONIC_VM_SPECS_DISK -p cpu_arch=x86_64| grep ' uuid ' | awk '{print $4}')

ironic port-create -n $NODE -a $MAC

ironic node-update $NODE add driver_info/pxe_deploy_kernel=$pxe_deploy_kernel
ironic node-update $NODE add driver_info/pxe_deploy_ramdisk=$pxe_deploy_ramdisk

ironic node-show $NODE
