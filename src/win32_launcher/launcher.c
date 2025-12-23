#include <stdio.h>
#include <stdlib.h>
#include <windows.h>
#include <unistd.h>
#include <sys/stat.h>
#include <string.h>

struct LAUNCHER_CONF {
	const char *python_runtime_search[4];
	const char *doc_dirs[4];
	const char *script;
	const char *ini;
	const char *console_title;
	};

#include "launcher_conf.h"

/*
** This function, written mostly in standard C, does the stuff we
** care about it. Windows Console Application stuff is handled
** in main().
*/
const char *launch(struct LAUNCHER_CONF conf, int argc, char *argv[])
	{
	char startup_dir[256];
	const char *python_runtime;
	char env_path[1024];
	char env_launcher[256];
	char env_lang[64];
	char command[256];

	struct stat statbuf;
	int i;

	/* Get the full path to the directory which contains this program.
	   (It is the current working directory.) */
	if(getcwd(startup_dir, sizeof(startup_dir)) != startup_dir)
		{
		char msg[256];
		snprintf(msg, sizeof(msg), "getcwd() failed: %s\n", strerror(errno));
		return strdup(msg);
		}
	printf("startup_dir: %s\n", startup_dir);

	printf("Searching for Python runtime...\n");
	for(i=0; (python_runtime = conf.python_runtime_search[i]); i++)
		{
		printf(" Trying %s\n", python_runtime);
		if(stat(python_runtime, &statbuf) == 0)
			{
			printf("  OK\n");
			break;
			}
		}
	if(!python_runtime)
		{
		return "Could not find Win32 runtime in any of the expected places.";
		}

	printf("Searching for documents directory...\n");
	{
	const char *template;
	char docdir[1024];
	int ret;
	for(i=0; conf.doc_dirs[i]; i++)
		{
		template = conf.doc_dirs[i];
		snprintf(docdir, sizeof(docdir), template, getenv("USERPROFILE"));
		printf(" Trying %s...\n", docdir);
		if((ret = stat(docdir, &statbuf)) == 0)
			{
			printf("  OK\n");
			break;
			}
		}
	if(ret != 0)
		{
		printf("  Creating %s\n", docdir);
		if(mkdir(docdir) != 0)
			{
			char msg[256];
			snprintf(msg, sizeof(msg), "mkdir(\"%s\") failed: %s\n", docdir, strerror(errno));
			return strdup(msg);
			}
		}
	if(chdir(docdir) != 0)
		{
		char msg[256];
		snprintf(msg, sizeof(msg), "chdir(\"%s\") failed: %s\n", docdir, strerror(errno));
		return strdup(msg);
		}
	}

	/* Add the bin directory in the Python runtime to the PATH. */
	snprintf(env_path, sizeof(env_path), "PATH=%s\\%s\\bin;%s", startup_dir, python_runtime, getenv("PATH"));
	printf("New %s\n", env_path);
	putenv(env_path);

	/* Set language */
	{
	TCHAR language[32];
	int result = GetPrivateProfileString(
		TEXT("Win32"), 				/* section */
		TEXT("ui_language"), 		/* key */
		TEXT(""), 					/* default */
		language, sizeof(language), 
		TEXT(conf.ini)				/* file */
		);
	if(strlen(language))
		{
		printf("Language: %s\n", language);
		snprintf(env_lang, sizeof(env_lang), "LANG=%s", language);\
		putenv(env_lang);
		}
	}

	/* This fixes pesky problems. */
	putenv("PYTHONIOENCODING=utf-8");

	/* Tell Python code path of this launcher so that it can integrate it into Explorer. */
	snprintf(env_launcher, sizeof(env_launcher), "LAUNCHER=%s", argv[0]);
	putenv(env_launcher);

	/* Run the Python interpreter with the script name as argument. */
	snprintf(command, sizeof(command), "python \"%s\\Code\\%s\"", startup_dir, conf.script);
	for(i=1; i<argc; i++)
		{
		int used = strlen(command);
		snprintf(command+used, sizeof(command)-used, " \"%s\"", argv[i]);
		}
	printf("Command: %s\n", command);

	if(system(command) != 0)
		{
		char msg[256];
		snprintf(msg, sizeof(msg), "Can't launch Python: %s\n", strerror(errno));
		return strdup(msg);
		}

	return NULL;
	}

int main(int argc, char *argv[])
	{
	HWND window = GetForegroundWindow();
	BOOL own_console = FALSE;

	if(argc >= 2 && strcmp(argv[1], "--show-console") == 0)
		{
		HWND existing_window = FindWindow(NULL, conf.console_title);
		if(existing_window)
			{
			ShowWindow(existing_window, SW_RESTORE);
			return 0;
			}
		else
			{
			fprintf(stderr, "No existing console found.\n");
			return 1;
			}
		}

	/* If the cursor is not at the top left, we assume we have our own console. */
	{
	HANDLE hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
	CONSOLE_SCREEN_BUFFER_INFO csbi;
	if(GetConsoleScreenBufferInfo(hStdOutput, &csbi))
		{
		own_console = (BOOL)(csbi.dwCursorPosition.X == 0 && csbi.dwCursorPosition.Y == 0);
		}
	}

	/* If not launched from CMD, */
	if(own_console)
		{
		/* Hide the console window. */
		ShowWindow(window, SW_HIDE);

		/* Set its title. */
		SetConsoleTitle(conf.console_title);

		/* Find SetConsoleIcon in the DLL. */
		typedef BOOL (WINAPI *PSetConsoleIcon)(HICON);
		static PSetConsoleIcon SetConsoleIcon;
		SetConsoleIcon = (PSetConsoleIcon)GetProcAddress(GetModuleHandle(("kernel32")), "SetConsoleIcon");

		/* Select the 2nd icon from the resource file. */
		HICON hIcon = LoadIcon(GetModuleHandle(0), "icon2");
		SetConsoleIcon(hIcon);
		}

	/* Here is the important stuff. */
	const char *error_msg = launch(conf, argc, argv);

	/* If the important stuff failed, display a Windows dialog box
	   and unhide this console. */
	if(error_msg)
		{
		MessageBox(0,
			error_msg,
			"Failed to Launch Program",		/* title */
			MB_OK
			);
		if(own_console)
			{
			ShowWindow(window, SW_RESTORE);
			printf("Press any key to close this window.\n");
			getchar();
			}
		return 1;
		}
	else
		{
		printf("Launcher exiting after successful run.\n");
		return 0;
		}
	}

