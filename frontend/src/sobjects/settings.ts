import { CompSObject } from "./compSObject"
import { ExposedAttributeInfo, Inspector } from "../inspector/inspector"
import { OptionsEditor } from "../inspector/OptionEditor"
import { bindTopicCookie } from "../utils"
import { DictTopic } from "objectsync-client"
import { print } from "../devUtils"
import { Workspace } from "./workspace"

export class Settings extends CompSObject{
    inspector: Inspector = new Inspector()
    entries: DictTopic<string,any>

    protected onStart(): void {
        this.inspector.mount(Workspace.instance.leftSidebar,'Settings')
        this.addFrontendSettings()
        this.entries = this.getAttribute('entries')
        this.link(this.entries.onSet,this.udpateEntries)
        this.udpateEntries()
    }

    private udpateEntries(){
        // adapt to inspector format
        const exposedAttrInfos: Map<string,ExposedAttributeInfo[]> = new Map()
        for(const [key,value] of this.entries.getValue()){
            const name = value.display_name
            if(!exposedAttrInfos.has(name)){
                exposedAttrInfos.set(name,[])
            }
            exposedAttrInfos.get(name).push(value)
        }
        this.inspector.update(exposedAttrInfos)
        this.addFrontendSettings()
    }
    
    private addFrontendSettings(){
        let editor = new OptionsEditor('theme',{'options':['blocks','light','simple','purple','fire']})
        this.inspector.addEditor(editor,'Appearance')
        bindTopicCookie(editor.topic,'theme','blocks')
        editor.topic.onSet.add((value)=>{
            // Seamless theme change
            let old = document.getElementById('custom-css')
            old.id = ''
            let swap: HTMLLinkElement = old.cloneNode(true) as HTMLLinkElement
            swap.id = 'custom-css'
            swap.setAttribute('href',`./css/${value}/main.css`)
            document.head.append(swap)
            setTimeout(() => {
                old.remove()
            }, 200);
        })
    }
}