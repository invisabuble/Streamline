export class media {
    constructor (media_json) {
        this.media_json = media_json;
        this.content = {};

        console.log(media_json);
    }
}

export class content {
    constructor (content_json) {
        this.content_json = content_json;
        this.content = {};
    }
}