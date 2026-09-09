/*
 * mpqtool - tiny StormLib wrapper for reading/writing .SC2Map (MPQ) archives.
 *
 *   mpqtool list    <archive>
 *   mpqtool extract <archive> <archived-name> <out-path>
 *   mpqtool replace <archive> <archived-name> <local-path>
 *   mpqtool add     <archive> <archived-name> <local-path>
 *   mpqtool delete  <archive> <archived-name>
 *
 * Archived names use backslashes, matching how SC2 stores them
 * (e.g. "enUS.SC2Data\LocalizedData\TriggerStrings.txt").
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "StormLib.h"

static void die(const char *what, int ok)
{
    if (!ok) {
        fprintf(stderr, "FAIL %s (err %u)\n", what, SErrGetLastError());
        exit(1);
    }
}

static void *open_archive(const char *path, DWORD flags)
{
    HANDLE hMpq = NULL;
    die("SFileOpenArchive", SFileOpenArchive(path, 0, flags, &hMpq));
    return hMpq;
}

static void do_list(const char *archive)
{
    HANDLE hMpq = open_archive(archive, MPQ_OPEN_READ_ONLY);
    SFILE_FIND_DATA fd;
    HANDLE hFind = SFileFindFirstFile(hMpq, "*", &fd, NULL);
    if (hFind == NULL) {
        fprintf(stderr, "empty or unreadable archive (err %u)\n", SErrGetLastError());
    } else {
        do {
            printf("%10u  %s\n", fd.dwFileSize, fd.cFileName);
        } while (SFileFindNextFile(hFind, &fd));
        SFileFindClose(hFind);
    }
    SFileCloseArchive(hMpq);
}

static void do_extract(const char *archive, const char *name, const char *out)
{
    HANDLE hMpq = open_archive(archive, MPQ_OPEN_READ_ONLY);
    die("SFileExtractFile", SFileExtractFile(hMpq, name, out, SFILE_OPEN_FROM_MPQ));
    SFileCloseArchive(hMpq);
}

static void do_put(const char *archive, const char *name, const char *local, int replace)
{
    HANDLE hMpq = open_archive(archive, 0);
    DWORD flags = MPQ_FILE_COMPRESS;
    if (replace) flags |= MPQ_FILE_REPLACEEXISTING;
    die("SFileAddFileEx", SFileAddFileEx(hMpq, local, name, flags,
                                        MPQ_COMPRESSION_ZLIB, MPQ_COMPRESSION_NEXT_SAME));
    die("SFileFlushArchive", SFileFlushArchive(hMpq));
    SFileCloseArchive(hMpq);
}

static void do_delete(const char *archive, const char *name)
{
    HANDLE hMpq = open_archive(archive, 0);
    die("SFileRemoveFile", SFileRemoveFile(hMpq, name, 0));
    die("SFileFlushArchive", SFileFlushArchive(hMpq));
    SFileCloseArchive(hMpq);
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: mpqtool list|extract|replace|add|delete ...\n");
        return 2;
    }

    const char *cmd = argv[1];
    const char *archive = argv[2];

    if (!strcmp(cmd, "list") && argc == 3) {
        do_list(archive);
    } else if (!strcmp(cmd, "extract") && argc == 5) {
        do_extract(archive, argv[3], argv[4]);
    } else if (!strcmp(cmd, "replace") && argc == 5) {
        do_put(archive, argv[3], argv[4], 1);
    } else if (!strcmp(cmd, "add") && argc == 5) {
        do_put(archive, argv[3], argv[4], 0);
    } else if (!strcmp(cmd, "delete") && argc == 4) {
        do_delete(archive, argv[3]);
    } else {
        fprintf(stderr, "bad arguments\n");
        return 2;
    }
    return 0;
}
