import os
import subprocess
import threading
import stat

from xbmcswift2 import Plugin, xbmcgui, xbmc, xbmcaddon

from resources.lib.confighelper import ConfigHelper

STRINGS = {
    'name': 30000,
    'addon_settings': 30100,
    'full_refresh': 30101,
    'choose_ctrl_type': 30200,
    'enter_filename': 30201,
    'starting_mapping': 30202,
    'mapping_success': 30203,
    'set_mapping_active': 30204,
    'mapping_failure': 30205,
    'pair_failure_paired': 30206,
    'configure_first': 30207
}

plugin = Plugin()
Config = ConfigHelper()

addon_path = plugin.storage_path
addon_internal_path = xbmcaddon.Addon().getAddonInfo('path')


@plugin.route('/')
def index():
    items = [{
        'label': 'Games',
        'path': plugin.url_for(
            endpoint='show_games'
        )
    }, {
        'label': 'Settings',
        'path': plugin.url_for(
            endpoint='open_settings'
        )
    }]
    return plugin.finish(items)


@plugin.route('/settings')
def open_settings():
    plugin.open_settings()


@plugin.route('/actions/create-mapping')
def create_mapping():
    log('Starting mapping')

    controllers = ['XBOX', 'PS3', 'Wii']
    ctrl_type = xbmcgui.Dialog().select(_('choose_ctrl_type'), controllers)
    map_name = xbmcgui.Dialog().input(_('enter_filename'))

    if map_name == '':
        return

    progress_dialog = xbmcgui.DialogProgress()
    progress_dialog.create(
        _('name'),
        _('starting_mapping')
    )

    log('Trying to call subprocess')
    map_file = '%s/%s-%s.map' % (os.path.expanduser('~'), controllers[ctrl_type], map_name)

    mapping = subprocess.Popen(['stdbuf', '-oL', Config.get_binary(), 'map', map_file, '-input',
                                plugin.get_setting('input_device', unicode)], stdout=subprocess.PIPE)

    lines_iterator = iter(mapping.stdout.readline, b"")

    thread = threading.Thread(target=loop_lines, args=(progress_dialog, lines_iterator))
    thread.start()

    success = 'false'

    while True:
        xbmc.sleep(1000)
        if not thread.isAlive():
            progress_dialog.close()
            success = 'true'
            log('Done, created mapping file in: %s' % map_file)
            break
        if progress_dialog.iscanceled():
            mapping.kill()
            progress_dialog.close()
            success = 'canceled'
            log('Mapping canceled')
            break

    if os.path.isfile(map_file) and success == 'true':
        confirmed = xbmcgui.Dialog().yesno(
            _('name'),
            _('mapping_success'),
            _('set_mapping_active')
        )
        log('Dialog Yes No Value: %s' % confirmed)
        if confirmed:
            plugin.set_setting('input_map', map_file)
            return
        else:
            return

    else:
        if success == 'false':
            xbmcgui.Dialog().ok(
                _('name'),
                _('mapping_failure')
            )
        else:
            return


@plugin.route('/actions/pair-host')
def pair_host():
    code = launch_moonlight_pair()

    if len(code) > 1:
        line = code[1]
        if line == '':
            line = _('pair_failure_paired')
    else:
        line = code[0]

    xbmcgui.Dialog().ok(
        _('name'),
        line
    )


@plugin.route('/games')
def show_games():
    def context_menu():
        return [
            (
                _('addon_settings'),
                'XBMC.RunPlugin(%s)' % plugin.url_for(
                    endpoint='open_settings'
                )
            ),
            (
                _('full_refresh'),
                'XBMC.RunPlugin(%s)' % plugin.url_for(
                    endpoint='do_full_refresh'
                )
            )
        ]

    Config.dump_conf()
    game_storage = plugin.get_storage('game_storage')
    game_storage.clear()
    games = get_games()
    items = []
    for i, game in enumerate(games):
        label = game
        items.append({
            'label': label,
            'replace_context_menu': True,
            'context_menu': context_menu(),
            'path': plugin.url_for(
                endpoint='launch_game',
                game_id=game
            )
        })
    game_storage.sync()
    return plugin.finish(items)


@plugin.route('/games/all/refresh')
def do_full_refresh():
    return get_games()


@plugin.route('/games/launch/<game_id>')
def launch_game(game_id):
    log('Launching game %s' % game_id)
    configure_helper(Config, Config.get_binary())
    log('Reconfigured helper and dumped conf to disk.')
    subprocess.call([addon_internal_path+'/resources/lib/launch-helper-osmc.sh',
                     addon_internal_path+'/resources/lib/launch.sh',
                     addon_internal_path+'/resources/lib/moonlight-heartbeat.sh',
                     game_id,
                     Config.get_config_path()])


def launch_moonlight_pair():
    code = []
    process = subprocess.Popen([Config.get_binary(), 'pair', Config.get_host()], stdout=subprocess.PIPE)
    while True:
        line = process.stdout.readline()
        code.append(line)
        if not line:
            break
    return code


def loop_lines(dialog, iterator):
    for line in iterator:
        log(line)
        dialog.update(0, line)


def get_games():
    game_list = []
    list_proc = subprocess.Popen([Config.get_binary(), 'list', Config.get_host()], stdout=subprocess.PIPE)
    while True:
        line = list_proc.stdout.readline()
        log(line[3:])
        game_list.append(line[3:].strip())
        if not line:
            break
    return game_list


def get_binary():
    binary_locations = [
        '/usr/bin/moonlight',
        '/usr/local/bin/moonlight'
    ]

    for f in binary_locations:
        if os.path.isfile(f):
            return f

    return None


def configure_helper(config, binary_path):
    """

    :param config: ConfigHelper
    :param binary_path: string
    """
    config.configure(
        addon_path,
        binary_path,
        plugin.get_setting('host', unicode),
        plugin.get_setting('enable_custom_resolution', bool),
        plugin.get_setting('resolution_width', str),
        plugin.get_setting('resolution_height', str),
        plugin.get_setting('resolution', str),
        plugin.get_setting('framerate', str),
        plugin.get_setting('graphic_optimizations', bool),
        plugin.get_setting('remote_optimizations', bool),
        plugin.get_setting('local_audio', bool),
        plugin.get_setting('enable_custom_bitrate', bool),
        plugin.get_setting('bitrate', int),
        plugin.get_setting('packetsize', int),
        plugin.get_setting('enable_custom_input', bool),
        plugin.get_setting('input_map', str),
        plugin.get_setting('input_device', str)
    )

    config.dump_conf()

    return True


def check_script_permissions():
    st = os.stat(addon_internal_path+'/resources/lib/launch.sh')
    if not bool(st.st_mode & stat.S_IXUSR):
        os.chmod(addon_internal_path+'/resources/lib/launch.sh', st.st_mode | 0111)
        log('Changed file permissions for launch')

    st = os.stat(addon_internal_path+'/resources/lib/launch-helper-osmc.sh')
    if not bool(st.st_mode & stat.S_IXUSR):
        os.chmod(addon_internal_path+'/resources/lib/launch-helper-osmc.sh', st.st_mode | 0111)
        log('Changed file permissions for launch-helper-osmc')

    st = os.stat(addon_internal_path+'/resources/lib/moonlight-heartbeat.sh')
    if not bool(st.st_mode & stat.S_IXUSR):
        os.chmod(addon_internal_path+'/resources/lib/moonlight-heartbeat.sh', st.st_mode | 0111)
        log('Changed file permissions for moonlight-heartbeat')


def log(text):
    plugin.log.info(text)


def _(string_id):
    if string_id in STRINGS:
        return plugin.get_string(STRINGS[string_id]).encode('utf-8')
    else:
        log('String is missing: %s' % string_id)
        return string_id


if __name__ == '__main__':
    log('Launching Luna')
    check_script_permissions()
    if plugin.get_setting('host', unicode) and get_binary():
        if configure_helper(Config, get_binary()):
            plugin.run()
    else:
        xbmcgui.Dialog().ok(
            _('name'),
            _('configure_first')
        )
