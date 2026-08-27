import { media_container } from "./handler.js"

console.log("Streamline.js loaded!");

const host = "http://streamline.local:8080"

async function get_route(route) {
  const response = await fetch(`${host}/api/${route}`);
  return await response.json()
}

function attach_behaviors() {
  document.querySelectorAll('media_group').forEach(media_group => {
    media_group.addEventListener('wheel', (e) => {
      if (e.target.closest('episodes')) return;
      if (e.deltaY !== 0) {
        e.preventDefault();
        media_group.scrollLeft += e.deltaY;
      }
    });
  });

  document.querySelectorAll('media_content').forEach(content_element => {
    content_element.addEventListener('click', (e) => e.stopPropagation());
  });

  document.querySelectorAll('media').forEach(media_element => {
    media_element.addEventListener('click', () => {
      const wasExpanded = media_element.classList.contains('expanded');
      document.querySelectorAll('media.expanded').forEach(el => el.classList.remove('expanded'));
      if (!wasExpanded) media_element.classList.add('expanded');
    });
  });
}

async function streamline () {

    const files   = await get_route("get_file_list");
    const devices = await get_route("devices");

    // If the devices list is populated then delete the no av message.
    const selector = document.getElementById("selector");
    if (Object.keys(devices).length > 0) {
        selector.innerHTML = "";
    }

    for (const [ip, device] of Object.entries(devices)) {
        console.log(ip, device);
        const option = document.createElement("option");
        option.value = ip;
        option.textContent = device.device_info.friendlyName || ip;
        selector.appendChild(option);
    }

    for (const root of files) {
        for (const group of root.Info.Children) {
            new media_container(group, host);
        }
    }

    attach_behaviors();
}

streamline();