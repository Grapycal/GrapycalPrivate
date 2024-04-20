import { DictTopic, ObjectSyncClient } from "objectsync-client"
import { Linker } from "../component/linker"
import { Componentable } from "../component/componentable"
import { stringToElement } from "../utils"
import { PopupMenu } from "./popupMenu/popupMenu"
import { Workspace } from "../sobjects/workspace"

export class ExtensionsSetting extends Componentable{
    protected get template(): string { return `
    <div>
        <div class="sidebar-tab-title">
        <h1>Extensions</h1>
        <hr>
        </div>
        <h2>In Use</h2>
        <div class="card-gallery" ref="importedDiv"></div>
        <h2>Avaliable</h2>
        <div class="card-gallery"  ref="avaliableDiv"></div>
        <h2>Not Installed</h2>
        <div class="card-gallery"  ref="notInstalledDiv"></div>
        <button ref="refreshButton">Refresh</button>
    </div>
    `}
    objectsync: ObjectSyncClient
    importedExtensionsTopic: DictTopic<string,any>
    avaliableExtensionsTopic: DictTopic<string,any>
    notInstalledExtensionsTopic: DictTopic<string,any>
    importedDiv: HTMLElement
    avaliableDiv: HTMLElement
    notInstalledDiv: HTMLElement
    refreshButton: HTMLButtonElement
    cardTemplate = `
    <div class="card">
        <div class="card-image"></div>
        <div class="card-content">
            <span class="card-title"></span> <span class="card-version"></span>
            
        </div>
    </div>
    `

    removeButtonTemplate = '<button class="card-button" style="color:#ff5555;" title="remove">—</button>'
    importButtonTemplate = '<button class="card-button" style="color:#44dd44;" title="import">+</button>'
    installButtonTemplate = '<button class="card-button" style="color:#44dd44;" title="install">⇩</button>'
    reloadButtonTemplate = '<button class="card-button" style="color:#5599ff;" title="reload">↻</button>'


    cards: {imported:{[name:string]:HTMLElement},avaliable:{[name:string]:HTMLElement},not_installed:{[name:string]:HTMLElement}} = {
        imported:{},
        avaliable:{},
        not_installed:{}
    }
    constructor(){
        super()

        this.objectsync = Workspace.instance.objectsync //TODO: do not steal the objectsync from workspace like this

        this.importedExtensionsTopic = this.objectsync.getTopic('imported_extensions',DictTopic<string,any>)
        for(let [name,extension] of this.importedExtensionsTopic.getValue()){
            this.addCard(extension,'imported')
        }
        this.linker.link(this.importedExtensionsTopic.onAdd,(name,newExtension)=>{
            this.addCard(newExtension,'imported')
        })
        this.linker.link(this.importedExtensionsTopic.onPop,(name,oldExtension)=>{
            this.cards.imported[name].remove()
        })
        this.linker.link(this.importedExtensionsTopic.onChangeValue,(name,newExtension)=>{
            this.cards.imported[name].remove()
            this.addCard(newExtension,'imported')
        })
        
        this.avaliableExtensionsTopic = this.objectsync.getTopic('avaliable_extensions',DictTopic<string,any>)
        for(let [name,extension] of this.avaliableExtensionsTopic.getValue()){
            this.addCard(extension,'avaliable')
        }
        this.linker.link(this.avaliableExtensionsTopic.onAdd,(name,newExtension)=>{
            this.addCard(newExtension,'avaliable')
        })
        this.linker.link(this.avaliableExtensionsTopic.onPop,(name,oldExtension)=>{
            this.cards.avaliable[name].remove()
        })
        this.linker.link(this.avaliableExtensionsTopic.onChangeValue,(name,newExtension)=>{
            this.cards.avaliable[name].remove()
            this.addCard(newExtension,'avaliable')
        })

        this.notInstalledExtensionsTopic = this.objectsync.getTopic('not_installed_extensions',DictTopic<string,any>)
        for(let [name,extension] of this.notInstalledExtensionsTopic.getValue()){
            this.addCard(extension,'not_installed')
        }
        this.linker.link(this.notInstalledExtensionsTopic.onAdd,(name,newExtension)=>{
            this.addCard(newExtension,'not_installed')
        })
        this.linker.link(this.notInstalledExtensionsTopic.onPop,(name,oldExtension)=>{
            this.cards.not_installed[name].remove()
        })
        this.linker.link(this.notInstalledExtensionsTopic.onChangeValue,(name,newExtension)=>{
            this.cards.not_installed[name].remove()
            this.addCard(newExtension,'not_installed')
        })

        this.refreshButton.addEventListener('click',()=>{
            this.objectsync.makeRequest('refresh_extensions')
        })
    }

    addCard(newExtension: any, status: 'imported' | 'avaliable' | 'not_installed'){
        let card: HTMLElement = document.createElement('div')
        card.innerHTML = this.cardTemplate
        card = card.firstElementChild as HTMLElement
        card.querySelector<HTMLSpanElement>('.card-title').innerText = newExtension.name
        card.querySelector<HTMLSpanElement>('.card-version').innerText = newExtension.version
        //card.querySelector<HTMLDivElement>('.card-image').style.backgroundImage = `url(${newExtension.icon})`
        card.querySelector<HTMLDivElement>('.card-image').style.backgroundImage = `url(https://imgur.com/xwG2FSr.jpg)`

        const cardContent = card.querySelector<HTMLDivElement>('.card-content')
        if(status == 'imported'){
            this.addButtonToCard(card,this.removeButtonTemplate,()=>{
                this.objectsync.makeRequest('unimport_extension',{extension_name:newExtension.name})
            })
            this.addButtonToCard(card,this.reloadButtonTemplate,()=>{
                this.objectsync.makeRequest('update_extension',{extension_name:newExtension.name})
            })
        }

        if(status == 'avaliable'){
            this.addButtonToCard(card,this.importButtonTemplate,()=>{
                this.objectsync.makeRequest('import_extension',{extension_name:newExtension.name})
            })
        }

        if(status == 'not_installed'){
            this.addButtonToCard(card,this.installButtonTemplate,()=>{
                this.objectsync.makeRequest('install_extension',{extension_name:newExtension.name})
            })
        }

        card.addEventListener('contextmenu',(e)=>{
            e.preventDefault()
            e.stopPropagation()
            let popup = Workspace.instance.popupMenu
            popup.openAt(e.clientX,e.clientY)
            if(status == 'imported'){
                popup.addOption('Reload',()=>{
                    this.objectsync.makeRequest('update_extension',{extension_name:newExtension.name})
                })
                popup.addOption('Remove from workspace',()=>{
                    this.objectsync.makeRequest('unimport_extension',{extension_name:newExtension.name})
                })
            }else{
                popup.addOption('Import to workspace',()=>{
                    this.objectsync.makeRequest('import_extension',{extension_name:newExtension.name})
                })
            }
        })

        this.cards[status][newExtension.name] = card
        if(status == 'imported'){
            this.importedDiv.appendChild(card)
            this.sortCards(this.importedDiv)
        }else if(status == 'avaliable'){
            this.avaliableDiv.appendChild(card)
            this.sortCards(this.avaliableDiv)
        }else if(status == 'not_installed'){
            this.notInstalledDiv.appendChild(card)
            this.sortCards(this.avaliableDiv)
        }
    }

    addButtonToCard(card:HTMLElement,buttonTemplate:string,onClick:()=>void){
        let button = stringToElement(buttonTemplate)
        button.addEventListener('click',onClick)
        card.querySelector<HTMLDivElement>('.card-content').appendChild(button)
    }

    sortCards(div:HTMLElement){
        let cards = Array.from(div.querySelectorAll('.card'))
        cards.sort((a,b)=>{
            let aTitle = a.querySelector<HTMLDivElement>('.card-title').innerText
            let bTitle = b.querySelector<HTMLDivElement>('.card-title').innerText
            //always put builtin nodes at the top
            if(aTitle.startsWith('grapycal_builtin')) return -1
            return aTitle.localeCompare(bTitle)
        })
        cards.forEach(card=>div.appendChild(card))
    }
}