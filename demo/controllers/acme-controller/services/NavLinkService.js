const navLinksJson = require('../data/nav_links.json');

class NavLinkService {
    constructor() {
        this.navLinks = navLinksJson;
    }

    getNavLinks() {
        return this.navLinks || [];
    }

    getCustomNavLinks() {
        return this.customNavLinks || [];
    }

    registerCustomLinks(links) {
        this.customNavLinks = links;
    }

    clearLinkClasses() {
        this.navLinks.forEach(navLink => delete navLink.class);
        this.customNavLinks.forEach(navLink => delete navLink.class);
    }

    setNavLinkActive(url) {
        const navLink = this.navLinks.find(navLink => navLink.url === url);
        if (navLink) {
            navLink.class = 'active';
        }
    }

    setCustomNavLinkActive(url) {
        const customNavLink = this.customNavLinks.find(navLink => navLink.url === url);
        if (customNavLink) {
            customNavLink.class = 'active';
        }
    }
}

module.exports = NavLinkService