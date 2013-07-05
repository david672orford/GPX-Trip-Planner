#include <stdio.h>
#include <stdlib.h>
#include <windows.h>
#include <unistd.h>
#include <sys/stat.h>

int main(int argc, char *argv[])
	{
	/* Change to this directory before doing anything else. */
	const char working_directory[] = "GPX";

	/* The Python runtime should be bin\python.exe in one
	   of these directories. This is relative to working_directory.
	*/
	const char *python_runtime_search[] = {"..\\Win32_Runtime", "..\\..\\Win32_Runtime", NULL};

	/* Python script to run */
	const char script[] = "..\\Code\\gpx-trip-planner.py";

	struct stat statbuf;
	int i;
	const char *python_runtime;
	char new_path[1024];
	char win32_launcher[256];
	char command[256];

	/* Minimize the console window and set its title. */
	HWND hwnd_win = GetForegroundWindow();
	ShowWindow(hwnd_win, SW_MINIMIZE);
	SetConsoleTitle("GPX Trip Planner Debug Console");

	/* Change to the directory where the applications data files are stored. */
	if(chdir(working_directory) != 0)
		{
		fprintf(stderr, "\n");
		fprintf(stderr, "chdir(\"%s\") failed: %s\n", working_directory, strerror(errno));
		return 1;
		}

	/* Find the Python runtime directory. */
	for(i=0; (python_runtime = python_runtime_search[i]); i++)
		{
		printf("Trying %s\n", python_runtime);
		if(stat(python_runtime, &statbuf) == 0)
			{
			printf("  OK\n");
			break;
			}
		}
	if(!python_runtime)
		{
		MessageBox(0,
			"Could not find Win32 runtime in any of the expected places.",
			"The Snake is Missing",		/* title */
			MB_OK
			);
		return 1;
		}

	/* So that the Python code can later find this launcher */
	snprintf(win32_launcher, sizeof(win32_launcher), "LAUNCHER=%s", argv[0]);
	putenv(win32_launcher);

	/* Add the bin directory in the Python runtime to the PATH. */
	snprintf(new_path, sizeof(new_path), "PATH=%s\\bin;%s", python_runtime, getenv("PATH"));
	printf("New %s\n", new_path);
	putenv(new_path);

	/* Hack to set language */
	if(strstr(argv[0], "-ru.exe"))
		putenv("LANG=ru");

	/* This fixes problems. */
	putenv("PYTHONIOENCODING=utf-8");

	/* Run the Python interpreter with the script name as argument. */
	snprintf(command, sizeof(command), "python %s", script);
	if(system(command) != 0)
		{
		fprintf(stderr, "\n");
		fprintf(stderr, "system(\"%s\") failed: %s\n", command, strerror(errno));
		return 1;
		}

	printf("Launcher exiting.\n");
	return 0;
	}

