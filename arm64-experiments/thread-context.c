#include <windows.h>
#include <stdio.h>
static HANDLE event;
static volatile LONG stopped,ready;
static DWORD WINAPI worker(void *wait) {
 InterlockedExchange(&ready,1);
 if(wait) WaitForSingleObject(event,INFINITE);
 else while(!stopped) InterlockedCompareExchange(&stopped,0,0);
 return 0;
}
int main(void) {
 event=CreateEventW(0,TRUE,FALSE,0);
 for(int mode=1;mode>=0;mode--) {
  ready=0;stopped=0;ResetEvent(event);
  HANDLE thread=CreateThread(0,0,worker,(void*)(ULONG_PTR)mode,0,0);
  if(!thread)return 2;
  while(!ready)Sleep(1);
  for(int i=0;i<20;i++) {
   Sleep(1);
   CONTEXT ctx={0};ctx.ContextFlags=CONTEXT_FULL;
   printf("mode=%d iter=%d suspend\n",mode,i);fflush(stdout);
   if(SuspendThread(thread)==(DWORD)-1)return 3;
   printf("context query\n");fflush(stdout);
   if(!GetThreadContext(thread,&ctx)){printf("context failed %lu\n",GetLastError());return 4;}
   if(!ctx.Rip || !ctx.Rsp)return 5;
   printf("rip=%llx rsp=%llx resume\n",(unsigned long long)ctx.Rip,(unsigned long long)ctx.Rsp);fflush(stdout);
   if(ResumeThread(thread)==(DWORD)-1)return 6;
  }
  InterlockedExchange(&stopped,1);SetEvent(event);
  if(WaitForSingleObject(thread,5000)!=WAIT_OBJECT_0)return 7;
  CloseHandle(thread);printf("PASS context mode=%s iterations=20\n",mode?"blocking wait":"JIT loop");fflush(stdout);
 }
 CloseHandle(event);return 0;
}
