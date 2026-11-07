#include <jni.h>
extern int pipe(int*),dup(int),dup2(int,int),close(int),fflush(void*);
extern long read(int,void*,unsigned long);
extern int hoshino_probe_main(void);
JNIEXPORT jstring JNICALL Java_org_hoshino_diagnostics_GpuProbe_probe(JNIEnv *env,jclass cls) {
 (void)cls;
 int fds[2]; if(pipe(fds))return (*env)->NewStringUTF(env,"FAIL: output pipe");
 int saved=dup(1);
 if(saved<0 || dup2(fds[1],1)<0){if(saved>=0)close(saved);close(fds[0]);close(fds[1]);return (*env)->NewStringUTF(env,"FAIL: output redirection");}
 close(fds[1]);
 int result=hoshino_probe_main();
 fflush(0);dup2(saved,1);close(saved);
 char output[8192];unsigned long used=0;long count;
 while(used<sizeof(output)-1 && (count=read(fds[0],output+used,sizeof(output)-1-used))>0)used+=(unsigned long)count;
 close(fds[0]); output[used]=0;
 if(result && used==0)return (*env)->NewStringUTF(env,"FAIL: native Vulkan probe");
 return (*env)->NewStringUTF(env,output);
}
