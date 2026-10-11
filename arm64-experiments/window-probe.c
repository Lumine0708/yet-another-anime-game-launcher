#define UNICODE
#include <windows.h>
#include <stdio.h>
#include <string.h>
static BOOL CALLBACK check(HWND wnd, LPARAM ignored) {
 DWORD pid; WCHAR image[32768]; DWORD length=32768; RECT rect={0},outer={0};
 GetWindowThreadProcessId(wnd,&pid);
 HANDLE p=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,pid);
 if(!p)return TRUE;
 BOOL ok=QueryFullProcessImageNameW(p,0,image,&length);CloseHandle(p);
 if(!ok)return TRUE;
 char path[32768];WideCharToMultiByte(CP_UTF8,0,image,-1,path,sizeof(path),0,0);
 if(!strstr(path,"YuanShen.exe"))return TRUE;
 BOOL client=GetClientRect(wnd,&rect),position=GetWindowRect(wnd,&outer);
 DWORD_PTR result;BOOL responsive=SendMessageTimeoutW(wnd,WM_NULL,0,0,SMTO_ABORTIFHUNG,1000,&result)!=0;
 printf("pid=%lu visible=%d client_ok=%d client=%ldx%ld rect_ok=%d outer=%ldx%ld style=%llx exstyle=%llx responsive=%d\n",pid,IsWindowVisible(wnd),client,rect.right-rect.left,rect.bottom-rect.top,position,outer.right-outer.left,outer.bottom-outer.top,(unsigned long long)GetWindowLongPtrW(wnd,GWL_STYLE),(unsigned long long)GetWindowLongPtrW(wnd,GWL_EXSTYLE),responsive);
 return TRUE;
}
int main(void) {
 DEVMODEW mode={0};mode.dmSize=sizeof(mode);BOOL display=EnumDisplaySettingsW(NULL,ENUM_CURRENT_SETTINGS,&mode);
 printf("screen=%dx%d display_ok=%d display=%lux%lu\n",GetSystemMetrics(SM_CXSCREEN),GetSystemMetrics(SM_CYSCREEN),display,mode.dmPelsWidth,mode.dmPelsHeight);
 BOOL ok=EnumWindows(check,0);
 printf("EnumWindows=%d\n",ok);return ok?0:3;
}
