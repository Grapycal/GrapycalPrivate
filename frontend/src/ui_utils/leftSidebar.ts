import { Componentable } from "../component/componentable"
import { Workspace } from "../sobjects/workspace"
import { as } from "../utils"
import { About } from "./about"
import { ExtensionsSetting } from "./extensionsSettings"


export class LeftSidebar extends Componentable {
    /**
    * The left sidebar is a tabbed interface with the following tabs:
    * - File View
    * - Node List
    * - Extensions
    * - Settings
    * - Examples
    * - About
    */

    protected get template(): string {
        return`
        <div class="sidebar sidebar-left" id="sidebar-left">
            <div class="sidebar-tab-selector">
            <button class="sidebar-tab-btn" id="tab-btn-file-view"><div class="sidebar-tab-btn-icon">📁</div></button>
            <button class="sidebar-tab-btn" id="tab-btn-node-list"><div class="sidebar-tab-btn-icon" title="nodes">📜</div></button>
            <button class="sidebar-tab-btn" id="tab-btn-extensions-setting"><div class="sidebar-tab-btn-icon">🚀</div></button>
            <button class="sidebar-tab-btn" id="tab-btn-settings"><div class="sidebar-tab-btn-icon">🛠️</div></button>
            <button class="sidebar-tab-btn" id="tab-btn-about" title="about">
                <img src="icon.png" alt="icon" width="27" height="27"></img>
            </button>
            </div>
            <div ref="sidebarContainer" class = "sidebar-container">
            <div slot="About" class="sidebar-tab" id="tab-about" style="display: none;">
            </div>
    
            <div slot="FileView" class="sidebar-tab" id="tab-file-view" style="display: none;">
            </div>
    
            <div slot="NodeLibrary" class="sidebar-tab" id="tab-node-list" style="display: none;">
            </div>

            <div slot="ExtensionsSetting" class="sidebar-tab" id="tab-extensions-setting" style="display: none;">
            </div>

            <div slot="Settings" class="sidebar-tab" id="tab-settings" style="display: none;">
            </div>
    
            </div>
        </div>`
    }

    tabs = new Map<HTMLButtonElement, HTMLDivElement>();
    sidebarContainer: HTMLDivElement;

    constructor() {
        super();
        this.mount(Workspace.instance)
        new ExtensionsSetting().mount(this);
        new About().mount(this);

        // buttons are #tab-btn-<name>
        // tabs are #tab-<name>
        for (let button of this.htmlItem.baseElement.getElementsByClassName('sidebar-tab-btn')) {
            let name = button.id.split('tab-btn-')[1];
            let tab = this.htmlItem.getHtmlEl('tab-' + name);
            this.tabs.set(as(button, HTMLButtonElement), as(tab, HTMLDivElement));
            
            this.link2(button, 'click', ()=>this.switchTab(as(button, HTMLButtonElement)));
            tab.style.display = 'none';
        }
        this.switchTab(document.getElementById('tab-btn-node-list') as HTMLButtonElement)
    }

    switchTab(button: HTMLButtonElement) {
        let tab = this.tabs.get(button)
        if(tab.style.display === 'none'){
            tab.style.display = 'block';
            button.classList.add('active');
            this.sidebarContainer.classList.remove('collapsed')
        }else{
            tab.style.display = 'none';
            button.classList.remove('active');
            this.sidebarContainer.classList.add('collapsed')
        }

        this.tabs.forEach((tab_, button) => {
            if (tab_ !== tab) {
                tab_.style.display = 'none';
                button.classList.remove('active');
            }
        });
    }

}