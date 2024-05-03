const fs = require('node:fs')
const path = require('node:path')

// .interpreter_list will be put in app.asar.unpacked because we need to modify it
// during development, since app.asar isn't in the path, the replace won't affect anything
// after the application is packed, by replacing app.asar with app.asar.unpacked,
// we can get access to the unpacked file and modify it
const interpreterListPath = path
	.join(__dirname, ".interpreter_list")
	.replace("app.asar", "app.asar.unpacked")


const interpreterList = () => 
	fs.readFileSync(interpreterListPath, 'utf8')
		.split('\n')
		.filter((line) => line !== '')
		.map((line) => ({ location: line.slice(1), using: line.charAt(0) == 'O' }))

const updateList = (list) => {
	fs.writeFileSync(
		interpreterListPath, 
		list.map((item) => `${item.using ? 'O' : 'X'}${item.location}`).join('\n')
	);
}

const addInterpreter = (loc) => {
	let list = interpreterList()
	list.push({ location: loc, using: false })
	updateList(list)

	return list
}

const select = (loc) => {
	let list = interpreterList()
	for (let i = 0; i < list.length; i++) {
		list[i].using = (list[i].location === loc)
	}
	updateList(list)

	return list
}

const currentInterpreter = () => {
	return interpreterList().find((interpreter) => interpreter.using)
}

module.exports = { interpreterList, addInterpreter, select, currentInterpreter }