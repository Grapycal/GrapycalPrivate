import { FloatTopic, StringTopic } from "objectsync-client"
import { Control } from "./control"
import { print } from "../../devUtils"
import { as, getImageFromClipboard } from "../../utils"
import { Workspace } from "../workspace"


export class ImageControl extends Control {
    
    protected get template (){return `
    <div class="control" tabindex=0>
        <img class="control-image full-height full-width" id="image">
    </div>
    `}

    protected get style(){return`
    .focused{
        outline: 1px solid #ffffff;
    }
    .control{
        background: #eee url('data:image/svg+xml,\
           <svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" fill-opacity="0.7">\
                    <rect width="400" height="400" />\
                    <rect x="200" width="200" height="200" />\
                    <rect y="200" width="200" height="200" />\
                    </svg>');
        background-size: 20px 20px;
        overflow: hidden; /* needed for the resize handle */
        resize: both;
        min-width: 100%;
    }
    `}

    private width = this.getAttribute("width", FloatTopic)
    private height = this.getAttribute("height", FloatTopic)

    protected onStart(): void {
        super.onStart()
        let base = as(this.htmlItem.baseElement, HTMLDivElement)
        let image = this.htmlItem.getEl("image", HTMLImageElement)
        let imageTopic = this.getAttribute("image", StringTopic)
        this.link(imageTopic.onSet, (newValue) => {
            // set the image data (jpg)
            image.src = "data:image/jpg;base64," + newValue
            this.node.moved.invoke()
        })

        base.onfocus = () => {
            base.classList.add("ImageControl-focused")
            this.link2(document, "paste", this.onPaste)
        }
        base.onblur = () => {
            base.classList.remove("ImageControl-focused")
            this.unlink2(document, "paste")
        }

        // eat drag events
        this.eventDispatcher.onDrag.add(this.node.moved.invoke)

        this.link(this.eventDispatcher.onDragEnd, (e) => {
            this.objectsync.record(() => {
                if(base.offsetWidth != this.width.getValue())
                    this.width.set(base.offsetWidth)
                if(base.offsetHeight != this.height.getValue())
                    this.height.set(base.offsetHeight)
            })
        })

        this.link(this.width.onSet, (newValue) => {
            base.style.width = newValue + "px"
        })

        this.link(this.height.onSet, (newValue) => {
            base.style.height = newValue + "px"
        })

    }


    onPaste(e: ClipboardEvent) {
        getImageFromClipboard(e, (base64String) => {
            // we message must < 4MB
            // but we will limit it to 2MB because change of StringTopic also sends old value
            if (base64String.length > 2000000) {
                Workspace.instance.appNotif.add("Image is too large. Max size is 2MB")
                return
            }
            let imageTopic = this.getAttribute("image", StringTopic)
            imageTopic.set(base64String)
        })
    }

}