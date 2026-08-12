console.log("Streamline.js Loaded!");

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


function RenderFileList(entries) {
    const list = document.getElementById("file-list");
    list.innerHTML = "";

    for (const entry of entries) {
        const item = document.createElement("li");
        item.textContent = entry.name;

        if (entry.type === "directory") {
            item.onclick = () => LoadLibrary(entry.path);
        }

        if (entry.type === "file") {
            item.onclick = () => Player(item, entry.path);
        }

        list.appendChild(item);
    }
}

async function LoadLibrary(path = "") {
    const response = await fetch(`/api/library?path=${encodeURIComponent(path)}`);
    const entries = await response.json();
    RenderFileList(entries);
}

async function Player(item, file = "") {
    item.classList.add("highlighted");
    console.log(file);
    const response = await fetch(`api/player?file=${file}`)
} 