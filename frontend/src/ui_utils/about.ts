import { Componentable } from "../component/componentable"

export class About extends Componentable{
    protected get template(): string { return `
    <div>
        <img src="https://i.imgur.com/hEnU3MI.png" alt="banner" width="100%" style="margin-top: 10px;"></img>
        <div class="sidebar-tab-title">

        <h1>About</h1>
        </div>
        <hr>


        Grapycal is designed with the goal to align with human perception at best, while being powerful with the help of Python, its backend.

        <br><br>

        If you're new, you may be unfamiliar with the syntax, but you'll soon find it easy to use! These may help you get started:
        <ul>
        <li><a href="https://docs.grapycal.com/latest/docs/">docs.grapycal.com</a></li>
        <li>📁 Files > 💡Example workspaces</li>
    </div>
    `}
}