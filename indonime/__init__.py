"""Indonime TUI — search → select → play loop."""
import argparse
import importlib
import os
import pkgutil
import time

from . import player
from .ui import (
    console, print_banner, print_header, print_step,
    print_success, print_error, print_warning, print_info, print_separator,
    make_episode_table, make_postplay_actions, make_footer,
    make_progress_bar, styled_status, make_style, Palette,
)

import plugins
import requests
from InquirerPy import inquirer
from ext import pdrain, megaNZ

_SESSION = requests.Session()


def _play_episode(episode_url, plugin, custom_style):
    """Resolve stream and play. Returns True if played successfully."""
    with console.status(styled_status("🔍 Resolving stream...")):
        dl_links = plugin.downloads(episode_url)

    options = []
    opt_map = {}
    for res, servers in dl_links.items():
        for s_name, s_url in servers.items():
            if any(x in s_name.lower() for x in ['pdrain', 'pixeldrain', 'mega']):
                label = f'[{res}] {s_name}'
                options.append({'name': label, 'value': s_url})
                opt_map[s_url] = label

    if not options:
        print_warning("No compatible servers found.")
        return False

    selected_opt = inquirer.select(
        message='📥  Select quality & server:',
        choices=options,
        style=custom_style,
    ).execute()
    if not selected_opt:
        return False
    server_url = selected_opt
    last_selected_server_name = opt_map[server_url]

    final_target = None
    is_temp = False

    # ── Continuous progress bar: 0% → 100% until mpv is ready ──
    if 'mega' in last_selected_server_name.lower():
        final_mega_url = None
        with make_progress_bar() as progress:
            task = progress.add_task(
                f"[{Palette.primary}]🔓 Resolving Mega link...",
                total=100,
            )

            # Phase 1: resolve HTTP redirect (show 0-10%)
            progress.update(task, completed=1)
            try:
                resp = _SESSION.get(server_url, allow_redirects=True, timeout=15)
                curr = resp.url
                if "mega.nz" in curr and ("#" in curr or "#!" in curr):
                    final_mega_url = curr
                else:
                    print_error("Redirect tidak mengarah ke Mega.")
                    return False
            except Exception as e:
                print_error(f"Requests Error: {e}")
                time.sleep(3)
                return False

            if not final_mega_url:
                print_error("Timeout: Gagal mendapatkan link Mega.")
                return False

            if "#!" in final_mega_url:
                final_mega_url = final_mega_url.replace("#!", "file/").replace("!", "#", 1)

            progress.update(task, completed=10,
                description=f"[{Palette.highlight}]📥 Buffering stream...")

            # Phase 2: start streaming, buffer until ready
            try:
                f_id = final_mega_url.split("file/")[1].split("#")[0]
                stream = megaNZ.resolve_mega_file_parallel(final_mega_url, f_id, console)
                if stream is None:
                    return False
                path, ready, stop, dl_thread, prog_info = stream

                progress.update(task, completed=15)

                # Phase 3: track buffer fill level from 15% to 99%
                # When bt=0: slowly climb 15-18% (waiting for first chunk measure)
                # When bt>0: climb 18-99% based on actual buffer progress
                _last_done = -1
                _stall_t0 = time.time()
                # ponytail: 20s stall timeout, beats hanging forever
                while not ready.is_set():
                    done = prog_info[0]
                    bt = prog_info[2]

                    if done == _last_done and time.time() - _stall_t0 > 20:
                        print_warning("Buffering stalled (>20s no progress). Check connection or retry.")
                        return False
                    if done != _last_done:
                        _last_done = done
                        _stall_t0 = time.time()

                    if bt > 0:
                        # Buffer target known — real buffer progress
                        pct = 10 + (done / bt * 85)
                    else:
                        # Buffer target not yet calculated (first ~8MB)
                        # Climb from 15% to ~18% during initial chunk
                        pct = 10 + 5 + min(done / max(1, 8 * 1024 * 1024) * 3, 3)

                    progress.update(task, completed=min(pct, 99))
                    time.sleep(0.15)

                progress.update(task, completed=100)

            except Exception as e:
                print_error(f"Gagal Streaming: {e}")
                time.sleep(3)
                return False

        # Progress bar done -> launch mpv
        print_step("🚀 Launching mpv player...")
        player.play_with_mpv(path, is_temp_file=True, cleanup=False)
        stop.set()
        dl_thread.join(timeout=10)
        if os.path.exists(path):
            os.remove(path)
        return True

    else:
        # PixelDrain path (indeterminate pulse bar)
        with make_progress_bar() as progress:
            task = progress.add_task(
                f"[{Palette.secondary}]🌀 Bypassing PixelDrain link...",
                total=None,
            )
            import threading as _th
            result_holder = [None]
            def _do_scrape():
                result_holder[0] = pdrain.scrape(server_url)
            scrape_thread = _th.Thread(target=_do_scrape, daemon=True)
            scrape_thread.start()
            while scrape_thread.is_alive():
                time.sleep(0.1)
            final_target = result_holder[0]

        if final_target:
            print_step("🚀 Launching mpv player...")
            return player.play_with_mpv(final_target, is_temp_file=is_temp)
        else:
            print_error("Stream resolution failed.")
            return False


def _episode_nav(episode_list, plugin, custom_style, back_label='<< BACK', show_banner=True):
    """Episode pick → play → post-play loop. Returns 'back' or 'quit'."""
    idx = 0
    while True:
        if show_banner:
            print_banner()
        print_header("📋 EPISODES", "🎬")
        console.print(make_episode_table(episode_list))
        print_separator()

        ep_choices = [
            {'name': f'  EP{i+1:02d}  —  {ep["title"][:50]}', 'value': i}
            for i, ep in enumerate(episode_list)
        ]
        ep_choices.append({'name': f'  ↩  {back_label}', 'value': 'back'})

        selected = inquirer.select(
            message='▶  Select episode:',
            choices=ep_choices,
            default=idx,
            style=custom_style,
            qmark="",
        ).execute()

        if selected == 'back' or selected is None:
            from plugins._base import cache_clear
            cache_clear()
            return 'back'
        idx = selected

        print_header("🎬 NOW PLAYING", "▶")
        if not _play_episode(episode_list[idx]['url'], plugin, custom_style):
            time.sleep(2)
            return 'back'

        print_separator()

        post_choices = make_postplay_actions(idx, len(episode_list))
        cmd = inquirer.select(
            message="🎮  Command:",
            choices=post_choices,
            style=custom_style,
            qmark="",
        ).execute()

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
    available_providers = [
        m.name for m in pkgutil.iter_modules(plugins.__path__)
        if not m.name.startswith('_')
    ]

    while True:
        print_banner()

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

        print_header("🔎 SEARCHING", "🔎")
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

        selected_url = next(
            item['url'] for item in results
            if item['title'] == selected_title
        )

        print_header("📋 EPISODES", "🎬")
        with console.status(styled_status("Fetching episode list...")):
            episode_list = _plugin.episodes(selected_url)

        if not episode_list:
            print_warning("No episodes found.")
            time.sleep(2)
            continue

        if _episode_nav(
            episode_list, _plugin, custom_style,
            back_label='<< BACK TO SEARCH', show_banner=True
        ) == 'quit':
            break

    print_banner()
    make_footer()
    print_success("Thanks for using Indonime! ~ Sayonara ~")


def _search_mode(query, provider='otakudesu'):
    """One-shot search → play → exit."""
    custom_style = make_style()
    print_banner()

    try:
        plugin = importlib.import_module(f'plugins.{provider}')
    except Exception as e:
        print_error(f"Plugin error: {e}")
        input('[Press Enter]')
        return

    print_header("🔎 SEARCHING", "🔎")
    with console.status(styled_status(f'Searching for "{query}"...')):
        results = plugin.search_anime(query)

    if not results:
        print_warning("No results found.")
        input('[Press Enter]')
        return

    choices = [item['title'] for item in results] + ['-- ABORT --']
    selected_title = inquirer.fuzzy(
        message='📺  Select title:',
        choices=choices,
        style=custom_style,
    ).execute()

    if selected_title == '-- ABORT --' or not selected_title:
        return

    selected_url = next(
        item['url'] for item in results
        if item['title'] == selected_title
    )

    print_header("📋 EPISODES", "🎬")
    with console.status(styled_status("Fetching episode list...")):
        episode_list = plugin.episodes(selected_url)

    if not episode_list:
        print_warning("No episodes found.")
        input('[Press Enter]')
        return

    _episode_nav(
        episode_list, plugin, custom_style,
        back_label='<< QUIT', show_banner=False
    )

    if player.current_mpv_process and player.current_mpv_process.poll() is None:
        player.current_mpv_process.wait()


def main():
    parser = argparse.ArgumentParser(
        description='Indonime — Subtitle Indonesia Anime Searcher'
    )
    parser.add_argument(
        'mode', nargs='?', default='tui',
        help='Mode: tui (interactive, default) or search <query>'
    )
    parser.add_argument('query', nargs='*', help='Search query')
    parser.add_argument(
        '-p', '--provider', default='otakudesu',
        choices=['otakudesu', 'anoboy'],
        help='Provider (default: otakudesu)'
    )
    args = parser.parse_args()

    if args.mode == 'search' and args.query:
        _search_mode(' '.join(args.query), args.provider)
    else:
        _tui_loop()