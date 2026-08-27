export class media_container {
  constructor (container_json) {
    this.container_json = container_json;

    this.title = container_json.Name;

    this.element = document.createElement("media_container");
    this.element.innerHTML = `<media_group_title class="media_content_text">${this.title}</media_group_title>`;

    this.media_group = document.createElement("media_group");

  }
}

export class media {
  constructor (img, title) {
    // Create all the media elements.
    this.media = document.createElement("media")
    this.media_card = document.createElement("media_card")
    this.media_card.innerHTML = `<img src="${img}">`;
    this.media_content = document.createElement("media_content")
    this.media_content.innerHTML = `<media_title class="media_content_text">${title}</media_title>`;
    this.media_desc = document.createElement("media_desc");

    // Append the elements together.
    this.media_content.appendChild(this.media_desc);
    this.media.appendChild(this.media_card);
    this.media.appendChild(this.media_content);
  }
}

export class movie extends media {
  constructor (img, title, desc) {
    super(img, title);
    this.medis_desc = desc;
  }
}

export class season extends media {
  constructor (img, title, desc) {
    super(img, title);
  }
}