#include <windows.h>
#include <stdio.h>
typedef unsigned (__cdecl *operation)(unsigned, unsigned long long *);
int main(void) {
    /* Save GS, write the requested selector, read it, then restore GS. */
    unsigned char code[] = {0x49,0x89,0xd1,0x65,0x4c,0x8b,0x04,0x25,0x30,0,0,0,0x4d,0x89,0x01,
        0x66,0x8c,0xea,0x89,0xc8,0x8e,0xe8,0x65,0x4c,0x8b,0x04,0x25,0x30,0,0,0,
        0x4d,0x89,0x41,0x08,0x66,0x8c,0xe8,0x0f,0xb7,0xc0,0x8e,0xea,0xc3};
    operation fn = VirtualAlloc(0,sizeof(code),MEM_RESERVE|MEM_COMMIT,PAGE_EXECUTE_READWRITE);
    if (!fn) return 2;
    memcpy((void*)fn,code,sizeof(code)); FlushInstructionCache(GetCurrentProcess(),(void*)fn,sizeof(code));
    unsigned inputs[] = {0,0x2b};
    int failed=0;
    for (int i=0;i<2;i++) {
        unsigned value=0, exception=0;
        unsigned long long teb[2]={0,0};
        __try {value=fn(inputs[i],teb);}
        __except(exception=GetExceptionCode(),EXCEPTION_EXECUTE_HANDLER) {}
        printf("selector=%04x result=%04x exception=%08x teb_before=%llx teb_after=%llx\n",inputs[i],value,exception,teb[0],teb[1]); fflush(stdout);
        failed |= exception || value!=inputs[i] || !teb[0] || teb[0]!=teb[1];
    }
    VirtualFree((void*)fn,0,MEM_RELEASE); printf("%s gs-selector\n",failed?"FAIL":"PASS"); return failed;
}
