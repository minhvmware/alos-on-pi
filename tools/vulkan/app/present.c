/* Android Vulkan surface/presentation probe, runs in an ordinary app sandbox. */
#define VK_NO_PROTOTYPES
#include <jni.h>
#include <vulkan/vulkan_core.h>
#include <vulkan/vulkan_android.h>
extern void *dlopen(const char*,int),*dlsym(void*,const char*);
extern int snprintf(char*,unsigned long,const char*,...);
#define LOAD(n) PFN_##n n=(PFN_##n)dlsym(lib,#n); if(!n)return (*env)->NewStringUTF(env,"FAIL: missing " #n);
#define CALL(x) do { result=(x); if(result!=VK_SUCCESS){stage=#x;goto cleanup;} } while(0)
JNIEXPORT jstring JNICALL Java_org_hoshino_diagnostics_GpuProbe_present(JNIEnv *env,jclass cls,jobject javaSurface) {
 (void)cls;
 void *android=dlopen("libandroid.so",2),*lib=dlopen("libvulkan.so",2);
 if(!android||!lib)return (*env)->NewStringUTF(env,"FAIL: Android/Vulkan library");
 void *(*fromSurface)(JNIEnv*,jobject)=dlsym(android,"ANativeWindow_fromSurface");
 void (*releaseWindow)(void*)=dlsym(android,"ANativeWindow_release");
 if(!fromSurface||!releaseWindow)return (*env)->NewStringUTF(env,"FAIL: native window API");
 LOAD(vkCreateInstance) LOAD(vkDestroyInstance) LOAD(vkCreateAndroidSurfaceKHR) LOAD(vkDestroySurfaceKHR)
 LOAD(vkEnumeratePhysicalDevices) LOAD(vkGetPhysicalDeviceProperties) LOAD(vkGetPhysicalDeviceQueueFamilyProperties)
 LOAD(vkGetPhysicalDeviceSurfaceSupportKHR) LOAD(vkGetPhysicalDeviceSurfaceCapabilitiesKHR) LOAD(vkGetPhysicalDeviceSurfaceFormatsKHR)
 LOAD(vkCreateDevice) LOAD(vkDestroyDevice) LOAD(vkGetDeviceQueue) LOAD(vkDeviceWaitIdle)
 LOAD(vkCreateSwapchainKHR) LOAD(vkDestroySwapchainKHR) LOAD(vkGetSwapchainImagesKHR)
 LOAD(vkCreateCommandPool) LOAD(vkDestroyCommandPool) LOAD(vkAllocateCommandBuffers) LOAD(vkBeginCommandBuffer) LOAD(vkEndCommandBuffer)
 LOAD(vkCmdPipelineBarrier) LOAD(vkCmdClearColorImage) LOAD(vkCreateSemaphore) LOAD(vkDestroySemaphore)
 LOAD(vkAcquireNextImageKHR) LOAD(vkQueueSubmit) LOAD(vkQueuePresentKHR) LOAD(vkQueueWaitIdle)
 VkInstance instance=VK_NULL_HANDLE; VkSurfaceKHR surface=VK_NULL_HANDLE; VkDevice device=VK_NULL_HANDLE;
 VkSwapchainKHR swap=VK_NULL_HANDLE; VkCommandPool pool=VK_NULL_HANDLE;
 VkSemaphore ready=VK_NULL_HANDLE,finished=VK_NULL_HANDLE;
 void *window=fromSurface(env,javaSurface); if(!window)return (*env)->NewStringUTF(env,"FAIL: no Surface");
 VkResult result=VK_SUCCESS; const char *stage="presentation"; char report[512];
 const char *iext[]={"VK_KHR_surface","VK_KHR_android_surface"};
 VkApplicationInfo app={.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,.pApplicationName="HoshinoOS surface probe",.apiVersion=VK_API_VERSION_1_0};
 VkInstanceCreateInfo ici={.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,.pApplicationInfo=&app,.enabledExtensionCount=2,.ppEnabledExtensionNames=iext};
 CALL(vkCreateInstance(&ici,0,&instance));
 VkAndroidSurfaceCreateInfoKHR sci={.sType=VK_STRUCTURE_TYPE_ANDROID_SURFACE_CREATE_INFO_KHR,.window=window};
 CALL(vkCreateAndroidSurfaceKHR(instance,&sci,0,&surface));
 VkPhysicalDevice physical=VK_NULL_HANDLE,list[16];uint32_t n=16;
 CALL(vkEnumeratePhysicalDevices(instance,&n,list));
 for(uint32_t i=0;i<n;i++){VkPhysicalDeviceProperties p;vkGetPhysicalDeviceProperties(list[i],&p);if(p.vendorID==0x14e4&&p.deviceType==VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU){physical=list[i];break;}}
 if(!physical){result=VK_ERROR_INITIALIZATION_FAILED;stage="Broadcom device";goto cleanup;}
 VkQueueFamilyProperties families[32];n=32;vkGetPhysicalDeviceQueueFamilyProperties(physical,&n,families);
 uint32_t family=~0u;
 for(uint32_t i=0;i<n;i++){VkBool32 supported=0;CALL(vkGetPhysicalDeviceSurfaceSupportKHR(physical,i,surface,&supported));if(supported&&families[i].queueCount&&(families[i].queueFlags&VK_QUEUE_GRAPHICS_BIT)){family=i;break;}}
 if(family==~0u){result=VK_ERROR_INITIALIZATION_FAILED;stage="graphics/present queue";goto cleanup;}
 float priority=1;VkDeviceQueueCreateInfo qci={.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,.queueFamilyIndex=family,.queueCount=1,.pQueuePriorities=&priority};
 const char *dext[]={"VK_KHR_swapchain"};
 VkDeviceCreateInfo dci={.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,.queueCreateInfoCount=1,.pQueueCreateInfos=&qci,.enabledExtensionCount=1,.ppEnabledExtensionNames=dext};
 CALL(vkCreateDevice(physical,&dci,0,&device));VkQueue queue;vkGetDeviceQueue(device,family,0,&queue);
 VkSurfaceCapabilitiesKHR caps;CALL(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(physical,surface,&caps));
 if(!(caps.supportedUsageFlags&VK_IMAGE_USAGE_TRANSFER_DST_BIT)){result=VK_ERROR_FORMAT_NOT_SUPPORTED;stage="surface transfer-destination capability";goto cleanup;}
 VkSurfaceFormatKHR formats[64];n=64;CALL(vkGetPhysicalDeviceSurfaceFormatsKHR(physical,surface,&n,formats));
 if(!n){result=VK_ERROR_FORMAT_NOT_SUPPORTED;stage="surface formats";goto cleanup;}
 VkSurfaceFormatKHR format=formats[0];for(uint32_t i=0;i<n;i++)if(formats[i].format==VK_FORMAT_R8G8B8A8_UNORM){format=formats[i];break;}
 if(format.format==VK_FORMAT_UNDEFINED)format.format=VK_FORMAT_R8G8B8A8_UNORM;
 if(caps.currentExtent.width==~0u){result=VK_ERROR_INITIALIZATION_FAILED;stage="surface has no fixed size yet";goto cleanup;}
 uint32_t count=caps.minImageCount+1;if(caps.maxImageCount&&count>caps.maxImageCount)count=caps.maxImageCount;
 VkCompositeAlphaFlagBitsKHR alpha=VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
 if(!(caps.supportedCompositeAlpha&alpha)){alpha=(VkCompositeAlphaFlagBitsKHR)(caps.supportedCompositeAlpha&(~caps.supportedCompositeAlpha+1u));}
 VkSwapchainCreateInfoKHR swapInfo={.sType=VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,.surface=surface,.minImageCount=count,.imageFormat=format.format,.imageColorSpace=format.colorSpace,.imageExtent=caps.currentExtent,.imageArrayLayers=1,.imageUsage=VK_IMAGE_USAGE_TRANSFER_DST_BIT,.imageSharingMode=VK_SHARING_MODE_EXCLUSIVE,.preTransform=caps.currentTransform,.compositeAlpha=alpha,.presentMode=VK_PRESENT_MODE_FIFO_KHR,.clipped=VK_TRUE};
 CALL(vkCreateSwapchainKHR(device,&swapInfo,0,&swap));VkImage images[16];n=16;CALL(vkGetSwapchainImagesKHR(device,swap,&n,images));
 VkCommandPoolCreateInfo pci={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,.queueFamilyIndex=family};CALL(vkCreateCommandPool(device,&pci,0,&pool));
 VkCommandBufferAllocateInfo cai={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,.commandPool=pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,.commandBufferCount=1};
 VkCommandBuffer command;CALL(vkAllocateCommandBuffers(device,&cai,&command));
 VkSemaphoreCreateInfo sem={.sType=VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};CALL(vkCreateSemaphore(device,&sem,0,&ready));CALL(vkCreateSemaphore(device,&sem,0,&finished));
 uint32_t index;CALL(vkAcquireNextImageKHR(device,swap,5000000000ULL,ready,VK_NULL_HANDLE,&index));
 VkCommandBufferBeginInfo begin={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT};CALL(vkBeginCommandBuffer(command,&begin));
 VkImageMemoryBarrier barrier={.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,.dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,.oldLayout=VK_IMAGE_LAYOUT_UNDEFINED,.newLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.image=images[index],.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};
 vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,0,0,0,1,&barrier);
 VkClearColorValue blue={{0.08f,0.25f,0.85f,1.0f}};vkCmdClearColorImage(command,images[index],VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,&blue,1,&barrier.subresourceRange);
 barrier.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;barrier.dstAccessMask=0;barrier.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;barrier.newLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
 vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,0,0,0,0,0,1,&barrier);CALL(vkEndCommandBuffer(command));
 VkPipelineStageFlags wait=VK_PIPELINE_STAGE_TRANSFER_BIT;
 VkSubmitInfo submit={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,.waitSemaphoreCount=1,.pWaitSemaphores=&ready,.pWaitDstStageMask=&wait,.commandBufferCount=1,.pCommandBuffers=&command,.signalSemaphoreCount=1,.pSignalSemaphores=&finished};
 CALL(vkQueueSubmit(queue,1,&submit,VK_NULL_HANDLE));
 VkPresentInfoKHR present={.sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,.waitSemaphoreCount=1,.pWaitSemaphores=&finished,.swapchainCount=1,.pSwapchains=&swap,.pImageIndices=&index};
 CALL(vkQueuePresentKHR(queue,&present));CALL(vkQueueWaitIdle(queue));
 snprintf(report,sizeof(report),"PASS: Android Vulkan surface, %ux%u swapchain, GPU color clear and presentation.\nThe surface below should be blue.",caps.currentExtent.width,caps.currentExtent.height);
cleanup:
 if(device)vkDeviceWaitIdle(device);
 if(ready)vkDestroySemaphore(device,ready,0);if(finished)vkDestroySemaphore(device,finished,0);
 if(pool)vkDestroyCommandPool(device,pool,0);if(swap)vkDestroySwapchainKHR(device,swap,0);
 if(device)vkDestroyDevice(device,0);if(surface)vkDestroySurfaceKHR(instance,surface,0);if(instance)vkDestroyInstance(instance,0);
 releaseWindow(window);
 if(result!=VK_SUCCESS)snprintf(report,sizeof(report),"FAIL: %s returned Vulkan error %d",stage,result);
 return (*env)->NewStringUTF(env,report);
}
