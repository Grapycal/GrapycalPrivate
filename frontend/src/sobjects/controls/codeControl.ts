import { EventTopic, IntTopic, StringTopic } from "objectsync-client"
import { Control } from "./control"
import {basicSetup, EditorView} from "codemirror"
import {autocompletion, CompletionResult, Completion, CompletionContext} from "@codemirror/autocomplete"
import {indentUnit} from "@codemirror/language"
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
            
        
            let match: {from: number, to: number, text: string}
            // from ... import statement completion
            match = context.matchBefore(/from\s+[^ ^\n]*\s+import\s+[^ ^\n]*/)
            if (match != null){
                this.makeRequest('suggestions', {text: match.text}, (response: Completion[]) => {
                    const completions = response
                    resolve({
                        from: match.from + match.text.lastIndexOf(" ") + 1, // +1 to skip the space
                        to: match.to,
                        options: completions,
                        validFor: /^\w*$/ // only allow words
                    })
                })
            }

            // import statement completion
            match = context.matchBefore(/^import\s.*$/)
            if (match != null){
                this.makeRequest('suggestions', {text: match.text}, (response: Completion[]) => {
                    const completions = response
                    resolve({
                        from: match.from + Math.max(match.text.lastIndexOf(" ") + 1, match.text.lastIndexOf(",")+1), // +1 to skip the space
                        to: match.to,
                        options: completions,
                        validFor: /[A-Za-z0-9_]*$/ // only allow words
                    })
                })
            }

            // from ... 
            match = context.matchBefore(/^from\s.*$/)
            if (match != null){
                this.makeRequest('suggestions', {text: match.text}, (response: Completion[]) => {
                    const completions = response
                    resolve({
                        from: match.from + match.text.lastIndexOf(" ")+1, // +1 to skip the space
                        to: match.to,
                        options: completions,
                        validFor: /[A-Za-z0-9_]*$/ // only allow words
                    })
                })
            }

            match = context.matchBefore(/[^ ^\n]*/) // match all characters except space and newline before the cursor
            

            this.makeRequest('suggestions', {text: match.text}, (response: Completion[]) => {
            const completions = response
            
            if (match.text.lastIndexOf(" ") >= match.text.lastIndexOf(".")) {
                completions.push(...this.keywords.map((keyword) => {
                    return {label: keyword, apply: keyword, info: keyword, type: "keyword"}
                }))
            }
            resolve({
                from: match.from + match.text.lastIndexOf(".") + 1, // +1 to skip the dot (.)
                to: match.to,
                options: completions,
                validFor: /^\w*$/ // only allow words
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
            indentUnit.of("    ")
        ],
          parent: this.htmlItem.baseElement,
        })

        this.editorView.dom.style.minWidth = "150px"
        this.editorView.dom.style.flexGrow = "1"

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

        // tab is 4 spaces
        this.editorView.dom.addEventListener("keydown", (e) => {
            if (e.key === "Tab") {
                e.preventDefault()
                // if the selection is empty, insert 4 spaces
                if(this.editorView.state.selection.ranges[0].from === this.editorView.state.selection.ranges[0].to){
                    this.editorView.dispatch({
                        changes: {from: this.editorView.state.selection.ranges[0].from, to: this.editorView.state.selection.ranges[0].to, insert: "    "},
                        selection: {anchor: this.editorView.state.selection.ranges[0].to + 4, head: this.editorView.state.selection.ranges[0].to + 4}
                    })
                }else{
                    // if there is a selection, indent it
                    const from = this.editorView.state.selection.ranges[0].from
                    const to = this.editorView.state.selection.ranges[0].to
                    const lines = this.editorView.state.doc.sliceString(from, to).split("\n")
                    const indentedLines = lines.map((line) => "    " + line)
                    const indentedText = indentedLines.join("\n")
                    this.editorView.dispatch({
                        changes: {from: from, to: to, insert: indentedText},
                        selection: {anchor: from, head: to + 4 * lines.length}
                    })
                
                }
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
