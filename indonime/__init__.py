"""Indonime TUI — search → select → play loop."""
import argparse
import importlib
import os
import pkgutil
import time

from . import player
from .ui import (
    console, print_banner, print_header, print_step,
    print_success, print_error, print_warning, print_separator,
    make_episode_table, make_footer, styled_status, make_style,
)

import plugins
import requests
from InquirerPy import inquirer
from ext import pdrain, megaNZ


def _play_episode(episode_url, plugin, custom_style):
    """Resolve stream and play. Returns True if played successfully."""
    with console.status(styled_status("🔍 Resolving stream...")):
        dl_links = plugin.downloads(episode_url)

    options = []
    for res, servers in dl_links.items():
        for s_name, s_url in servers.items():
            if any(x in s_name.lower() for x in ['pdrain', 'pixeldrain', 'mega']):
                options.append({'name': f'[{res}] {s_name}', 'value': s_url, 'raw_name': f'[{res}] {s_name}'})

    if not options:
        print_warning("No compatible servers found.")
        return False

    selected_opt = inquirer.select(message='📥  Select quality:', choices=options, style=custom_style).execute()
    if not selected_opt:
        return False
    server_url = selected_opt
    last_selected_server_name = next(opt['raw_name'] for opt in options if opt['value'] == server_url)

    final_target = None
    is_temp = False

    if 'mega' in last_selected_server_name.lower():
        final_mega_url = None
        with console.status(styled_status("🔓 Resolving Mega link...")):
            try:
                resp = requests.get(server_url, allow_redirects=True, timeout=15)
                curr = resp.url
                if "mega.nz" in curr and ("#" in curr or "#!" in curr):
                    final_mega_url = curr
                else:
                    print_error("Redirect tidak mengarah ke Mega.")
            except Exception as e:
                print_error(f"Requests Error: {e}")
                time.sleep(3)

        if final_mega_url:
            if "#!" in final_mega_url:
                final_mega_url = final_mega_url.replace("#!", "file/").replace("!", "#", 1)
            try:
                f_id = final_mega_url.split("file/")[1].split("#")[0]
                stream = megaNZ.resolve_mega_file_stream(final_mega_url, f_id, console)
                if stream is None:
                    return False
                path, ready, stop, dl_thread = stream
                print_step("Buffering...")
                ready.wait()  # ~2MB first, then launch mpv
                print_step("Launching mpv player...")
                player.play_with_mpv(path, is_temp_file=True, cleanup=False)
                # mpv exited — signal download thread, wait for it, then delete
                stop.set()
                dl_thread.join(timeout=10)
                if os.path.exists(path):
                    os.remove(path)
                return True
            except Exception as e:
                print_error(f"Gagal Streaming: {e}")
                time.sleep(3)
                return False
        else:
            print_error("Timeout: Gagal mendapatkan link Mega.")
            return False
    else:
        print_step("Bypassing PixelDrain link...")
        final_target = pdrain.scrape(server_url)

    if final_target:
        print_step("Launching mpv player...")
        return player.play_with_mpv(final_target, is_temp_file=is_temp)
    else:
        print_error("Stream resolution failed.")
        return False


def _episode_nav(episode_list, plugin, custom_style, back_label='<< BACK', show_banner=True, show_quality=True):
    """Episode pick -> play -> post-play. Returns 'back' or 'quit'."""
    idx = 0
    while True:
        if show_banner:
            print_banner()

        print_header("📋 EPISODES")
        console.print(make_episode_table(episode_list))
        print_separator()

        ep_choices = [{'name': f'  EP{str(i+1).zfill(2)}', 'value': i} for i, _ in enumerate(episode_list)]
        ep_choices.append({'name': f'  ↩ {back_label}', 'value': 'back'})
        selected = inquirer.select(message='▶  Select episode:', choices=ep_choices, default=idx, style=custom_style, qmark="").execute()
        if selected == 'back' or selected is None:
            return 'back'
        idx = selected

        print_header("🎬 NOW PLAYING")
        if not _play_episode(episode_list[idx]['url'], plugin, custom_style):
            time.sleep(2)
            return 'back'

        print_separator()
        post_choices = ['▶  NEXT', '◀  PREV', '↺  REPLAY', '✖  QUIT']
        if show_quality:
            post_choices.insert(-1, '⚙  QUALITY')
        cmd = inquirer.select(message="🎮  Command:", choices=post_choices, style=custom_style, qmark="").execute()

        if cmd == '▶  NEXT':
            if idx + 1 < len(episode_list):
                idx += 1
        elif cmd == '◀  PREV':
            if idx > 0:
                idx -= 1
        elif cmd in ('↺  REPLAY', '⚙  QUALITY'):
            continue
        else:
            return 'quit'


def _tui_loop():
    p_name = 'otakudesu'
    _last_plugin_name = None
    _plugin = None
    custom_style = make_style()
    available_providers = [m.name for m in pkgutil.iter_modules(plugins.__path__)
                           if not m.name.startswith('_')]

    while True:
        print_banner()

        # Lazy load / reload only on provider switch
        if p_name != _last_plugin_name:
            _plugin = importlib.import_module(f'plugins.{p_name}')
            _last_plugin_name = p_name

        is_switching = False
        try:
            prompt = inquirer.text(
                message='🔍  Search anime:',
                qmark='',
                instruction='[alt+p] switch provider',
                style=custom_style,
                validate=lambda x: True if is_switching else len(x) > 0,
            )
            @prompt.register_kb('alt-p')
            def _(event):
                nonlocal is_switching
                is_switching = True
                event.app.exit(result='/switch')
            result = prompt.execute()
        except KeyboardInterrupt:
            break

        if result == '/switch':
            new_p = inquirer.select(
                message='📡  Select provider:',
                choices=available_providers,
                qmark='',
                style=custom_style,
            ).execute()
            if new_p:
                p_name = new_p
            continue
        if not result:
            break

        print_header("🔎 SEARCHING")
        with console.status(styled_status(f'Searching for "{result}"...')):
            results = _plugin.search_anime(result)

        if not results:
            print_warning("No results found.")
            time.sleep(2)
            continue

        choices = [item['title'] for item in results] + ['-- ABORT --']
        selected_title = inquirer.fuzzy(
            message='📺  Select title:',
            choices=choices,
            style=custom_style,
        ).execute()
        if selected_title == '-- ABORT --' or not selected_title:
            continue

        selected_url = next(item['url'] for item in results if item['title'] == selected_title)

        print_header("📋 EPISODES")
        with console.status(styled_status("Fetching episode list...")):
            episode_list = _plugin.episodes(selected_url)

        if not episode_list:
            print_warning("No episodes found.")
            time.sleep(2)
            continue

        if _episode_nav(episode_list, _plugin, custom_style, back_label='<< BACK TO SEARCH', show_banner=True, show_quality=True) == 'quit':
            break

    print_banner()
    make_footer()
    print_success("Thanks for using Indonime! ~ Sayonara ~")


def _search_mode(query, provider='otakudesu'):
    """One-shot search -> play -> exit."""
    custom_style = make_style()
    print_banner()

    try:
        plugin = importlib.import_module(f'plugins.{provider}')
    except Exception as e:
        print_error(f"Plugin error: {e}")
        input('[Press Enter]')
        return

    print_header("🔎 SEARCHING")
    with console.status(styled_status(f'Searching for "{query}"...')):
        results = plugin.search_anime(query)

    if not results:
        print_warning("No results found.")
        input('[Press Enter]')
        return

    choices = [item['title'] for item in results] + ['-- ABORT --']
    selected_title = inquirer.fuzzy(message='📺  Select title:', choices=choices, style=custom_style).execute()
    if selected_title == '-- ABORT --' or not selected_title:
        return

    selected_url = next(item['url'] for item in results if item['title'] == selected_title)

    print_header("📋 EPISODES")
    with console.status(styled_status("Fetching episode list...")):
        episode_list = plugin.episodes(selected_url)

    if not episode_list:
        print_warning("No episodes found.")
        input('[Press Enter]')
        return

    _episode_nav(episode_list, plugin, custom_style, back_label='<< QUIT', show_banner=False, show_quality=False)

    if player.current_mpv_process and player.current_mpv_process.poll() is None:
        player.current_mpv_process.wait()


def main():
    parser = argparse.ArgumentParser(description='Indonime - Subtitle Indonesia Anime Searcher')
    parser.add_argument('mode', nargs='?', default='tui',
                        help='Mode: tui (interactive, default) or search <query>')
    parser.add_argument('query', nargs='*', help='Search query')
    parser.add_argument('-p', '--provider', default='otakudesu',
                        choices=['otakudesu', 'anoboy'], help='Provider (default: otakudesu)')
    args = parser.parse_args()

    if args.mode == 'search' and args.query:
        _search_mode(' '.join(args.query), args.provider)
    else:
        _tui_loop()
