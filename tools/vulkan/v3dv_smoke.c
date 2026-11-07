/* On-device Vulkan queue/buffer smoke test; no display or app preferences changed. */
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan_core.h>
extern int printf(const char *, ...);
extern void *dlopen(const char *, int);
extern void *dlsym(void *, const char *);
#define CHECK(x) do { VkResult r=(x); if(r!=VK_SUCCESS){printf("FAIL %s: %d\n",#x,r);return 1;} } while(0)
#define LOAD(name) PFN_##name name=(PFN_##name)dlsym(lib,#name); if(!name){printf("Missing %s\n",#name);return 1;}
int main(void) {
 void *lib=dlopen("libvulkan.so",2); if(!lib){printf("No Vulkan loader\n");return 1;}
 LOAD(vkCreateInstance) LOAD(vkEnumeratePhysicalDevices) LOAD(vkGetPhysicalDeviceProperties)
 LOAD(vkGetPhysicalDeviceQueueFamilyProperties) LOAD(vkCreateDevice) LOAD(vkGetDeviceQueue)
 LOAD(vkCreateBuffer) LOAD(vkGetBufferMemoryRequirements) LOAD(vkGetPhysicalDeviceMemoryProperties)
 LOAD(vkAllocateMemory) LOAD(vkBindBufferMemory) LOAD(vkCreateCommandPool) LOAD(vkAllocateCommandBuffers)
 LOAD(vkBeginCommandBuffer) LOAD(vkCmdFillBuffer) LOAD(vkCmdPipelineBarrier) LOAD(vkEndCommandBuffer)
 LOAD(vkQueueSubmit) LOAD(vkQueueWaitIdle) LOAD(vkMapMemory) LOAD(vkUnmapMemory)
 LOAD(vkDestroyCommandPool) LOAD(vkDestroyBuffer) LOAD(vkFreeMemory) LOAD(vkDestroyDevice) LOAD(vkDestroyInstance)
 VkApplicationInfo app={.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,.pApplicationName="HoshinoOS V3DV smoke",.apiVersion=VK_API_VERSION_1_0};
 VkInstanceCreateInfo ici={.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,.pApplicationInfo=&app};
 VkInstance instance; CHECK(vkCreateInstance(&ici,0,&instance));
 VkPhysicalDevice devices[16]; uint32_t n=16; CHECK(vkEnumeratePhysicalDevices(instance,&n,devices));
 VkPhysicalDevice physical=VK_NULL_HANDLE;
 for(uint32_t i=0;i<n;i++) { VkPhysicalDeviceProperties p; vkGetPhysicalDeviceProperties(devices[i],&p);
  printf("Device: %s vendor=0x%x type=%d Vulkan=%u.%u.%u\n",p.deviceName,p.vendorID,p.deviceType,VK_VERSION_MAJOR(p.apiVersion),VK_VERSION_MINOR(p.apiVersion),VK_VERSION_PATCH(p.apiVersion));
  if(p.vendorID==0x14e4 && p.deviceType==VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU) physical=devices[i];
 }
 if(!physical){printf("FAIL: no Broadcom hardware GPU\n");return 1;}
 VkQueueFamilyProperties families[32]; n=32; vkGetPhysicalDeviceQueueFamilyProperties(physical,&n,families);
 uint32_t family=~0u; for(uint32_t i=0;i<n;i++) if(families[i].queueCount && (families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT)){family=i;break;}
 if(family==~0u){printf("FAIL: no graphics queue\n");return 1;}
 float priority=1; VkDeviceQueueCreateInfo qci={.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,.queueFamilyIndex=family,.queueCount=1,.pQueuePriorities=&priority};
 VkDeviceCreateInfo dci={.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,.queueCreateInfoCount=1,.pQueueCreateInfos=&qci};
 VkDevice device; CHECK(vkCreateDevice(physical,&dci,0,&device)); VkQueue queue; vkGetDeviceQueue(device,family,0,&queue);
 VkBufferCreateInfo bci={.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,.size=4096,.usage=VK_BUFFER_USAGE_TRANSFER_DST_BIT,.sharingMode=VK_SHARING_MODE_EXCLUSIVE};
 VkBuffer buffer; CHECK(vkCreateBuffer(device,&bci,0,&buffer));
 VkMemoryRequirements req; vkGetBufferMemoryRequirements(device,buffer,&req);
 VkPhysicalDeviceMemoryProperties mem; vkGetPhysicalDeviceMemoryProperties(physical,&mem);
 uint32_t type=~0u; for(uint32_t i=0;i<mem.memoryTypeCount;i++) if((req.memoryTypeBits&(1u<<i)) && (mem.memoryTypes[i].propertyFlags&(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))==(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)){type=i;break;}
 if(type==~0u){printf("FAIL: no host-coherent memory for test\n");return 1;}
 VkMemoryAllocateInfo mai={.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,.allocationSize=req.size,.memoryTypeIndex=type};
 VkDeviceMemory memory; CHECK(vkAllocateMemory(device,&mai,0,&memory)); CHECK(vkBindBufferMemory(device,buffer,memory,0));
 VkCommandPoolCreateInfo pci={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,.queueFamilyIndex=family};
 VkCommandPool pool; CHECK(vkCreateCommandPool(device,&pci,0,&pool));
 VkCommandBufferAllocateInfo cai={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,.commandPool=pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,.commandBufferCount=1};
 VkCommandBuffer cmd; CHECK(vkAllocateCommandBuffers(device,&cai,&cmd));
 VkCommandBufferBeginInfo begin={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT};
 CHECK(vkBeginCommandBuffer(cmd,&begin)); vkCmdFillBuffer(cmd,buffer,0,4096,0x484f5348);
 VkMemoryBarrier barrier={.sType=VK_STRUCTURE_TYPE_MEMORY_BARRIER,.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,.dstAccessMask=VK_ACCESS_HOST_READ_BIT};
 vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&barrier,0,0,0,0);
 CHECK(vkEndCommandBuffer(cmd));
 VkSubmitInfo submit={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,.commandBufferCount=1,.pCommandBuffers=&cmd};
 CHECK(vkQueueSubmit(queue,1,&submit,VK_NULL_HANDLE)); CHECK(vkQueueWaitIdle(queue));
 uint32_t *mapped; CHECK(vkMapMemory(device,memory,0,4096,0,(void**)&mapped));
 for(uint32_t i=0;i<1024;i++) if(mapped[i]!=0x484f5348){printf("FAIL: GPU readback at %u\n",i);return 1;}
 vkUnmapMemory(device,memory); vkDestroyCommandPool(device,pool,0); vkDestroyBuffer(device,buffer,0); vkFreeMemory(device,memory,0); vkDestroyDevice(device,0); vkDestroyInstance(instance,0);
 printf("PASS: Broadcom Vulkan device, queue submission and 4096-byte GPU fill/readback\n"); return 0;
}
