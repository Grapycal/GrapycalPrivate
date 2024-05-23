import { ObjectSyncClient } from 'objectsync-client'
import { expose, print } from './devUtils'
import { ButtonControl } from './sobjects/controls/buttonControl'
import { CodeControl } from "./sobjects/controls/codeControl"
import { ImageControl } from './sobjects/controls/imageControl'
import { KeyboardControl } from './sobjects/controls/keyboardControl'
import { LinePlotControl } from './sobjects/controls/linePlotControl'
import { OptionControl } from './sobjects/controls/optionControl'
import { SliderControl } from './sobjects/controls/sliderControl'
import { TextControl } from './sobjects/controls/textControl'
import { ThreeControl } from './sobjects/controls/threeControl'
import { ToggleControl } from './sobjects/controls/toggleControl'
import { Edge } from './sobjects/edge'
import { Editor } from './sobjects/editor'
import { FileView } from './sobjects/fileView'
import { Node } from './sobjects/node'
import { NodeLibrary } from './sobjects/nodeLibrary'
import { Port } from './sobjects/port'
import { Root } from './sobjects/root'
import { Settings } from './sobjects/settings'
import { WebcamStream, Workspace } from './sobjects/workspace'
import { SoundManager } from './ui_utils/soundManager'
import { FetchWithCache } from './utils'

export const soundManager = new SoundManager();
const fetchWithCache = new FetchWithCache().fetch
export { fetchWithCache }

function tryReconnect(): void{
    if(Workspace.instance != null)
        Workspace.instance.appNotif.add('Connection to server lost. Reconnecting...',4000)
    fetch(getWsUrl().replace('ws://','http://'), {
        method: "HEAD",
        signal: AbortSignal.timeout(2000),
        mode: 'no-cors'
    })
    .then((response) => {
        window.location.reload();
    })
    .catch((error) => {
        print('failed to reconnect');
        // wait for 2 seconds before trying again
        setTimeout(tryReconnect, 2000);
    });
}

function documentReady(callback: Function): void {
    if (document.readyState === "complete" || document.readyState === "interactive")
        callback()
    else
        document.addEventListener("DOMContentLoaded", (event: Event) => {
            callback()
        })
}

function startObjectSync(wsUrl:string){
    const objectsync = new ObjectSyncClient(wsUrl,null,tryReconnect);

    objectsync.register(Root);
    objectsync.register(Workspace);
    objectsync.register(Editor);
    objectsync.register(Settings)
    objectsync.register(FileView)
    objectsync.register(Node);
    objectsync.register(Port);
    objectsync.register(Edge);
    objectsync.register(NodeLibrary);

    objectsync.register(TextControl)
    objectsync.register(ButtonControl)
    objectsync.register(ImageControl)
    objectsync.register(ThreeControl)
    objectsync.register(LinePlotControl)
    objectsync.register(OptionControl)
    objectsync.register(KeyboardControl)
    objectsync.register(SliderControl)
    objectsync.register(CodeControl)
    objectsync.register(ToggleControl)

    objectsync.register(WebcamStream)


    document.addEventListener('keydown', function(event) {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() == 'z') {
            event.preventDefault();
            objectsync.undo(null);
        }
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() == 'y') {
            event.preventDefault();
            objectsync.redo(null);
        }
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() == 's') {
            event.preventDefault();
            objectsync.makeRequest('ctrl+s');
        }
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() == 'q') {
            event.preventDefault();
            objectsync.makeRequest('exit');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
    },{capture: true});

    // for debugging
    expose('o',objectsync)
}

// from webpack config files
declare var __BUILD_CONFIG__: {
    isService: boolean,
    wsPort: number
}

// webpack define plugin will replace __BUILD_CONFIG__ with the injected value
const buildConfig = __BUILD_CONFIG__

function getWsUrl(): string{
    const wsUrlParam = new URLSearchParams(window.location.search).get('ws_url')
    if(wsUrlParam != null)
        return wsUrlParam
    if(buildConfig.wsPort == null)
        return `ws://${location.hostname}:${location.port}/ws`
    return `ws://${location.hostname}:${buildConfig.wsPort}/ws`
}

documentReady(() => {
    startObjectSync(getWsUrl())
})
