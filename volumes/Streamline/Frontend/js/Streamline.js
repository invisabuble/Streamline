

var selected_file = "";
var is_media_set = false;

async function Devices() {

    const response =
        await fetch("/api/devices");

    const devices =
        await response.json();

    const select =
        document.getElementById("device");

    select.innerHTML = "";

    for (const device of devices) {

        const option =
            document.createElement("option");

        option.value = device.ip;

        option.textContent =
            device.friendlyName ||
            device.ip;

        select.appendChild(option);
    }
}

function reset_dir () {
    LoadLibrary();
}


function RenderFileList(entries) {
    const list = document.getElementById("file-list");
    list.innerHTML = "";

    for (const entry of entries) {

        const item = new window.Generic_Dir(entry.type, list, entry.name);

        if (entry.type === "directory") {
            item.element.onclick = (event) => {
                event.stopPropagation();
                LoadLibrary(entry.path)
            };
        }

        if (entry.type === "file") {
            item.element.onclick = (event) => {
                event.stopPropagation();
                selected_file = entry.path
                item.element.classList.add("highlighted");
            }
        }
    }
}

async function LoadLibrary(path = "") {
    is_media_set = false;
    const response = await fetch(`/api/library?path=${encodeURIComponent(path)}`);
    const entries = await response.json();
    RenderFileList(entries);
}

async function set_media_file() {
    console.log("Setting media file.");
    is_media_set = true;
    var device = document.getElementById("device").value;
    const response = await fetch(`api/set_media_file?file=${selected_file}&device=${device}`);
} 

async function play () {
    if (!is_media_set) {
        set_media_file();
    }
    const response = await fetch("/api/play")
}

async function pause () {
    is_media_set = true;
    const response = await fetch("/api/pause")
}