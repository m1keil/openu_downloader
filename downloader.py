from gevent import monkey; monkey.patch_all()

import os
import gevent
import requests
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--course', required=True)
    parser.add_argument('-s', '--semester', required=True)
    parser.add_argument('-g', '--group', required=True)
    parser.add_argument('-e', '--education-center', required=True)
    parser.add_argument('-l', '--lesson', required=True)
    return parser.parse_args()


def get_chunklists(course, semester, group, center, lesson):
    url_tmpl = 'http://api.bynetcdn.com/Redirector/openu/manifest/' \
               'c{0}_{1}_{2}_{3}_{4}_mp4/HLS/' \
               'playlist.m3u8'
    url = url_tmpl.format(course, semester, group, center, lesson)
    print 'playlist: %s' % url

    r = requests.get(url)
    r.raise_for_status()

    content = r.content

    if 'JTMtwFWNpt' in content:
        print 'Error: video not found. Quitting.'
        exit(1)

    return {line.split('/')[-1]: line for line in content.split()
            if line.startswith('http')}


def get_files(chunklist_url):
    print 'chunklist: %s' % chunklist_url
    url = chunklist_url.rsplit('/', 1)[0]

    r = requests.get(chunklist_url)
    r.raise_for_status()

    content = r.content

    for line in content.split():
        if not line.startswith('#'):
            yield url + '/' + line


def download(url, path):
    fname = url.split('/')[-1]
    fpath = os.path.join(path, fname)
    if os.path.isfile(fpath):
        print 'File already exists: {}. Skipping'.format(fname)
        return

    print 'downloading: %s' % url
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.content

    with open(fpath, 'w') as fp:
        fp.write(data)


def concat_dir(path, save_path):
    file_list = os.listdir(path)
    # create dict of number: file
    files = {int(x.rsplit('_', 1)[1].split('.')[0]): os.path.join(path, x)
             for x in file_list}

    fnums = files.keys()
    fnums.sort()

    with open(save_path, 'a') as wf:
        for num in fnums:
            fpath = files[num]
            with open(fpath, 'r') as rf:
                wf.write(rf.read())


def main():
    args = parse_args()
    chunklists = get_chunklists(args.course,
                                args.semester,
                                args.group,
                                args.education_center,
                                args.lesson)

    # get lowest quality
    files = get_files(chunklists['chunklist_b400000.m3u8'])

    tmp_path = '/tmp/{0}/{1}'.format(args.course, args.lesson)
    try:
        os.makedirs(tmp_path)
    except OSError as e:
        print 'Unable to create dir: {}. {}.'.format(tmp_path, e.strerror)

    pool = gevent.pool.Pool(size=4)
    [pool.spawn(download, url, tmp_path) for url in files]
    pool.join()
    print '========================'
    print '== DONE'
    print '========================'

    save_path = os.path.join(os.getcwd(), args.course + '.ts')
    concat_dir(tmp_path, save_path)

    print 'Cache: %s' % tmp_path
    print 'Saved to: %s' % save_path


if __name__ == '__main__':
    main()
