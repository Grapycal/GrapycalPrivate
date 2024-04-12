import { ObjectSyncClient, ObjectTopic, StringTopic, GenericTopic, IntTopic, DictTopic} from "objectsync-client"
import { CompSObject } from "./compSObject";
import { EventDispatcher, GlobalEventDispatcher } from "../component/eventDispatcher"
import { Editor } from "./editor"
import { SelectionManager } from "../component/selectionManager"
import { Node } from "./node"
import { Edge } from "./edge"
import { Footer } from "../ui_utils/footer"
import { Buffer } from "buffer";
import { print } from "../devUtils"
import { NodeInspector } from "../ui_utils/nodeInspector"
import { PopupMenu } from "../ui_utils/popupMenu/popupMenu"
import { AppNotification } from "../ui_utils/appNotification"
import { ControlPanel } from "../ui_utils/controlPanel"
import { ExtensionsSetting } from "../ui_utils/extensionsSettings"
import { RightSideBar } from "../base/rightSidebar"
import { LeftSidebar } from "../ui_utils/leftSidebar"

export class Workspace extends CompSObject{
    public static instance: Workspace

    readonly main_editor = this.getAttribute('main_editor', ObjectTopic<Editor>)
    readonly nodeTypesTopic = this.objectsync.getTopic('node_types',DictTopic<string,any>)
    readonly slashCommandsTopic = this.objectsync.getTopic('slash_commands',DictTopic<string,any>)

    protected get template(): string { return `
        <div spellcheck="false" class="full-width full-height" style="display: flex; ">
          <!-- <header></header> -->
          <div class="main">
            <div slot="NodeLibrary"></div>
            <div slot="LeftSidebar"></div>
            <div slot="RightSideBar"></div>
        
            <div id="settings-page" class="settings-page">
              <div class="settings-page-overlay" id="settings-page-overlay"></div>
              <div class="settings-page-content">
        
              </div>
            </div>
          </div>
          <footer slot="Footer"></footer>
          <div slot="ControlPanel"></div>
          <div slot="AppNotification"></div>
        </div>
    `}

    /* ===== Element References ===== */

    popupMenu: PopupMenu
    appNotif: AppNotification
    selection: SelectionManager
    leftSidebar: LeftSidebar
    rightSidebar: RightSideBar

    /* ===== Other Properties ===== */
    readonly record: ObjectSyncClient['record']

    get clientId(){
        return this.objectsync.clientId
    }
    constructor(objectsync: ObjectSyncClient, id: string) {
        super(objectsync, id);
        Workspace.instance = this
        this.record = objectsync.record
    }
    protected onStart(): void {   
        this.mount(document.body)     
        document.addEventListener('contextmenu', function(event) {
            event.preventDefault();
        });

        this.leftSidebar = new LeftSidebar().mount(this)
        this.rightSidebar = new RightSideBar().mount(this)
        this.appNotif = new AppNotification().mount(this)
        this.popupMenu = new PopupMenu()
        this.selection = new SelectionManager(this)

        new Footer().mount(this)
        new ControlPanel().mount(this)

        this.appNotif.add('Workspace loaded. Have fun!', 5000)

        this.popupMenu.hideWhenClosed = true;
        (this.selection as any).name = 'selection'
        this.selection.onSelect.add((selectable)=>{
            let obj = selectable.object
            if(obj instanceof Node){
                NodeInspector.instance.addNode(obj)
            }
        })
        this.selection.onDeselect.add((selectable)=>{
            let obj = selectable.object
            if(obj instanceof Node){
                NodeInspector.instance.removeNode(obj)
            }
        })

        this.main_editor.getValue().eventDispatcher.onClick.add(()=>{
            if(GlobalEventDispatcher.instance.isKeyDown('Control')) return;
            if(GlobalEventDispatcher.instance.isKeyDown('Shift')) return;
            this.selection.clearSelection()
        })
        
        Footer.setStatus('Workspace loaded. Have fun!')
    }

    public openWorkspace(path:string){
        this.objectsync.makeRequest('open_workspace',{path:path})
    }

    public callSlashCommand(name:string,ctx:any){
        this.objectsync.makeRequest('slash_command',{name:name,ctx:ctx})
    }
}

export class WebcamStream extends CompSObject{
    image: StringTopic
    sourceClient: IntTopic
    stream: MediaStream = null
    interval:number = 200
    timer: NodeJS.Timeout

    protected onStart(): void {
        // (navigator.mediaDevices as any).getUserMedia = (navigator.mediaDevices as any).getUserMedia || (navigator.mediaDevices as any).webkitGetUserMedia || (navigator.mediaDevices as any).mozGetUserMedia || (navigator.mediaDevices as any).msGetUserMedia

        this.image = this.getAttribute('image', StringTopic)
        this.sourceClient = this.getAttribute('source_client', IntTopic)
        this.sourceClient.onSet.add((sourceClient)=>{
            if(sourceClient == Workspace.instance.clientId){
                this.startStreaming()
            }else{
                this.stopStreaming()
            }
        })
    }

    private startStreaming(){
        if (this.stream) return;
        (navigator.mediaDevices as any).getUserMedia( {video: { width: 480, height: 320 }, audio: false})
        .then((stream: MediaStream) => {
            console.log('got stream')
            this.stream = stream
            // start loop
            this.timer = setInterval(()=>{
                this.publish()
            },this.interval)
            video.srcObject = stream;

            video.setAttribute('autoplay', 'true');
            video.onloadeddata = () => {

                video.play();
            }
        })
        .catch(function(err: any) {
            console.error(err);
        })
    }

    private publish(){
        let image = getImageFromStream(this.stream)
        image.then((blob: Blob)=>{
            let reader = new FileReader()
            reader.onload = (event) => {
                let buf =Buffer.from( reader.result as ArrayBuffer)
                var base64String = buf.toString('base64')
                this.image.set(base64String)
            }
            reader.readAsArrayBuffer(blob)
        })
    }

    private stopStreaming(){
        if(this.stream==null) return;
        clearInterval(this.timer)
        this.stream = null
    }


}

const video = document.createElement('video');
const canvas = document.createElement('canvas');
const context = canvas.getContext('2d');

//https://stackoverflow.com/questions/62446301/alternative-for-the-imagecapture-api-for-better-browser-support
function getImageFromStream(stream: MediaStream) {

    if (false && 'ImageCapture' in window) {

      const videoTrack = stream.getVideoTracks()[0];
      const imageCapture = new (window as any).ImageCapture(videoTrack);
      return imageCapture.takePhoto({imageWidth: 48, imageHeight: 32});

    } else {



      return new Promise((resolve, reject) => {
          //const { videoWidth, videoHeight } = video;
          const { videoWidth, videoHeight } = {videoWidth: 480, videoHeight: 320};
          canvas.width = videoWidth;
          canvas.height = videoHeight;

          try {
            context.drawImage(video, 0, 0, videoWidth, videoHeight);
            canvas.toBlob(resolve, 'image/jpg');
          } catch (error) {
            reject(error);
          }
        });
    }

}
