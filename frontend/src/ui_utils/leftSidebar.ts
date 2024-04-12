import { Componentable } from "../component/componentable"
import { Workspace } from "../sobjects/workspace"
import { as } from "../utils"
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
            <button class="sidebar-tab-btn" id="tab-btn-3"><div class="sidebar-tab-btn-icon">🚀</div></button>
            <button class="sidebar-tab-btn" id="tab-btn-settings"><div class="sidebar-tab-btn-icon">🛠️</div></button>
            <button class="sidebar-tab-btn" id="tab-btn-1" title="about">
                <img src="icon.png" alt="icon" width="27" height="27"></img>
            </button>
            </div>
            <div ref="sidebarContainer" class = "sidebar-container">
            <div class="sidebar-tab" id="tab-1" style="display: none;">
    
                <img src="https://i.imgur.com/hEnU3MI.png" alt="banner" width="100%" style="margin-top: 10px;"></img>
                <div class="sidebar-tab-title">
    
                <h1>About</h1>
                </div>
                <hr>
    
    
                Grapycal is an open source project <a href="https://github.com/eri24816/Grapycal">[Github]</a>.
                Welcome to join and contribute!
                <br></br>
                Grapycal is designed with the goal to align with human perception at best, while being powerful with the help of Python, its backend.
    
                <br><br>
    
                If you're new, you may be unfamiliar with the syntax, but you'll soon find it easy to use! These may help you get started:
                <ul>
                <li><a href="https://wiki.grapycal.org/index.php?title=Grapycal_Wiki_ouO">wiki.grapycal.org</a></li>
                <li>📁 Files > 💡Example workspaces</li>
            </div>
    
            <div class="sidebar-tab" id="tab-file-view" style="display: none;">
                <div class="sidebar-tab-title">
                <h1>Files</h1>
    
                <hr>
                </div>
            </div>
    
            <div class="sidebar-tab" id="tab-node-list" style="display: none;">
                <div class="sidebar-tab-title">
                <h1>Node Library</h1>
                <hr>
                </div>
                Want more nodes? Extend the list at 🚀Extensions tab.
                <br></br>
                <div slot="NodeLibrary"></div>
    
            </div>
            <div class="sidebar-tab" id="tab-3" style="display: none;">
                <div class="sidebar-tab-title">
                <h1>Extensions</h1>
                <hr>
                </div>
                <h2>In Use</h2>
                <div class="card-gallery" id="imported-extensions"></div>
                <h2>Avaliable</h2>
                <div class="card-gallery"  id="avaliable-extensions"></div>
                <h2>Not Installed</h2>
                <div class="card-gallery"  id="not-installed-extensions"></div>
                <button id="refresh-extensions">Refresh</button>
            </div>
            <div slot="Settings" class="sidebar-tab" id="tab-settings" style="display: none;">
                <div class="sidebar-tab-title">
                <h1>Settings</h1>
                <hr>
                </div>
            </div>
    
            </div>
        </div>`
    }

    tabs = new Map<HTMLButtonElement, HTMLDivElement>();
    sidebarContainer: HTMLDivElement;

    constructor() {
        super();
        this.mount(Workspace.instance)
        new ExtensionsSetting(Workspace.instance.objectsync); //TODO: do not steal the objectsync from the workspace
        let root = document;
        // buttons are #tab-btn-<name>
        // tabs are #tab-<name>
        for (let button of this.htmlItem.baseElement.getElementsByClassName('sidebar-tab-btn')) {
            let name = button.id.split('tab-btn-')[1];
            let tab = root.getElementById('tab-' + name);
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