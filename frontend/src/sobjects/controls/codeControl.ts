import { EventTopic, IntTopic, StringTopic } from "objectsync-client"
import { Control } from "./control"
import { print } from "../../devUtils"
import { BindInputBoxAndTopic } from "../../ui_utils/interaction"
import { TextBox} from "../../utils"
import {basicSetup, EditorView} from "codemirror"
import {autocompletion, CompletionResult, Completion, CompletionContext} from "@codemirror/autocomplete"
import {python} from "@codemirror/lang-python"
import { basicDark } from "../../ui_utils/cmDarkTheme"

export class CodeControl extends Control {

    editorView: EditorView
    text = this.getAttribute("text", StringTopic)
    label = this.getAttribute("label", StringTopic)
    editable = this.getAttribute("editable", IntTopic)
    placeholder = this.getAttribute("placeholder", StringTopic)

    private lock = false
    protected template = `
    <div class="control flex-horiz" id="codecontrol">
        <div class="label" id="label"></div>
    </div>    
    `

    protected css: string = `
        #codecontrol {
            overflow: visible;
            display: flex;
        }
        .label{
            flex-shrink: 0;
            min-width: 0px;
        }
    `

    private keywords: string[] = ['False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield']

    private async myCompletions(context: CompletionContext): Promise<CompletionResult> {
        const promise = new Promise<CompletionResult>((resolve, reject) => {
            const info = context.matchBefore(/[^ ^\n]*/) // match all characters except space and newline before the cursor
            this.makeRequest('suggestions', {text: info.text}, (response: Completion[]) => {
                const completions = response
                
                if (info.text.lastIndexOf(" ") >= info.text.lastIndexOf(".")) {
                    completions.push(...this.keywords.map((keyword) => {
                        return {label: keyword, apply: keyword, info: keyword, type: "keyword"}
                    }))
                }
                print(info.text.lastIndexOf("."), info.text.lastIndexOf(" "))

                resolve({
                    from: info.from + info.text.lastIndexOf(".") + 1, // +1 to skip the dot (.)
                    to: info.to,
                    options: completions,
                    validFor: /^\w*$/
                })
            })
        })
        return promise
    }


    protected onStart(): void {
        super.onStart()
        this.myCompletions = this.myCompletions.bind(this)
        this.editorView =  new EditorView({
          extensions: [
            basicSetup,
            EditorView.updateListener.of(this.update.bind(this)),
            autocompletion({override: [this.myCompletions], closeOnBlur: false}),
            basicDark,
            python(),
        ],
          parent: this.htmlItem.baseElement,
        })

        this.editorView.dom.style.minWidth = "200px"

        // this.editorView.from
        this.editorView.dom.addEventListener("mousedown", (e) => {
            e.stopPropagation()
        })

        this.editorView.dom.addEventListener("dblclick", (e) => {
            e.stopPropagation()
        })
        // consume a scroll event
        this.editorView.dom.addEventListener("wheel", (e) => {
            if(this.editorView.hasFocus && this.editorView.dom.scrollHeight > this.editorView.dom.clientHeight){
                e.stopPropagation()
            }
        })

        this.link(this.text.onSet, (value) => {
            if (this.lock) return
            this.editorView.dispatch({changes: {from: 0, to: this.editorView.state.doc.length, insert: value}})
        })
    }

    protected update(e: any): void {
        this.lock = true
        this.text.set(e.state.doc.toString())
        this.lock = false
    }
}
