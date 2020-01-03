export class NavLink {
    constructor(label, url) {
        this.label = label || '';
        this.url = url || '/';
    }

    label: string;
    url: string;
}
