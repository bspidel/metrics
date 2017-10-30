import os
import sys
import json
import statsd
import logging
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

issues_api = "https://api.github.com/repos/unfoldingWord-dev/translationCore/issues?milestone={0}"


def getJSONfromURL(url, token=""):
    if token:
        raw = requests.get(url, auth=('token', token))
    else:
        raw = requests.get(url)
    return raw.json()

def push(metrics, host='localhost', port=8125, prefix=''):
    stats = statsd.StatsClient(host, port, prefix=prefix)
    for k,v in metrics.items():
        stats.gauge(k, v)

def catalog(gl_codes, metrics={}):
    catalog = getJSONfromURL('https://api.door43.org/v3/catalog.json')
    metrics['total_langs'] = len(catalog['languages'])
    metrics['gls_with_content'] = len([x for x in catalog['languages'] if x['identifier'] in gl_codes])
    all_resources = 0
    for x in catalog['languages']:
        for y in x['resources']:
            all_resources += 1
            if not 'resources_{}_langs'.format(y['identifier']) in metrics:
                metrics['resources_{}_langs'.format(y['identifier'])] =0
            metrics['resources_{}_langs'.format(y['identifier'])] +=1
    metrics['all_resources'] = all_resources
    logger.info(metrics)
    return metrics

def tD(metrics={}):
    langnames = getJSONfromURL('https://td.unfoldingword.org/exports/langnames.json')
    gl_codes = [x['lc'] for x in langnames if x['gw']]
    metrics['langs_all'] = len(langnames)
    metrics['langs_gls'] = len(gl_codes)
    metrics['langs_private_use'] = len([x for x in langnames if '-x-' in x['lc']])
    logger.info(metrics)
    return (metrics, gl_codes)

def github(metrics={}):
    release_api = 'https://api.github.com/repos/unfoldingWord-dev/{0}/releases'
    software = ['translationCore', 'ts-android', 'ts-desktop', 'uw-android']
    for x in software:
        metrics['software_{0}'.format(x)] = 0
        releases = getJSONfromURL(release_api.format(x))
        for entry in releases:
            for asset in entry['assets']:
                metrics['software_{0}'.format(x)] += asset['download_count']
    logger.info(metrics)
    return metrics

def play(metrics={}):
    metrics['ts-android_total'] = 1698
    metrics['uw-android_total'] = 1393
    metrics['tk-android_total'] = 713
    logger.info(metrics)
    return metrics

def getHoursRemaining(title):
    hours = 0
    if title.startswith('['):
        hours = int(title.split()[0].strip('[]'))
    return hours

def getMilestoneMetrics(issues):
    metrics = {}
    for item in issues:
        hours_key = 'hours_{0}'.format(item['assignee']['login'])
        issues_key = 'issues_{0}'.format(item['assignee']['login'])
        # Initialize variables
        if hours_key not in metrics:
            metrics[hours_key] = 0
        if issues_key not in metrics:
            metrics[issues_key] = 0
        # Increment
        metrics[hours_key] += getHoursRemaining(item['title'].strip())
        metrics[issues_key] += 1
    return metrics


if __name__ == "__main__":
    logging.basicConfig()
    td_metrics, gl_codes = tD()
    push(td_metrics, prefix="td")
    catalog_metrics = catalog(gl_codes)
    push(catalog_metrics, prefix="door43_catalog")
    github_metrics = github()
    push(github_metrics, prefix="github")
    play_metrics = play()
    push(play_metrics, prefix="play")

    # tC Dev Metrics
    github_token = os.getenv('GITHUB_TOKEN', False)
    if not github_token:
        logger.warn('Environment variable GITHUB_TOKEN not found.')
        sys.exit(1)
    issues = getJSONfromURL(issues_api.format('43'), github_token)
    milestone_metrics = getMilestoneMetrics(issues)
    logger.info(milestone_metrics)
    push(milestone_metrics, prefix="tc_dev")