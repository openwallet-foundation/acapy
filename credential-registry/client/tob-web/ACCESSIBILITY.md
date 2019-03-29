# Accessibility

This applications aims to meet or exceed the [World Wide Web Consortium (W3C) Web Content Accessibility Guidelines (WCAG) 2.0](https://www.w3.org/TR/WCAG20/).

## Tested Assistive Technologies

The following technologies are recommended to be tested with this application, chosen because of their popularity and coverage using data from http://webaim.org/projects/screenreadersurvey6/:

1. JAWS IE 11 on Windows 10
2. NVDA Firefox (evergreen) on Windows 10 
3. VoiceOver on Mac OS (should get iOS coverage)
4. Colour Constrast Checker from https://webaim.org/resources/contrastchecker/

## General Advice

1. Use native HTML5 elements/attributes where possible, e.g., `<header><nav><label><input required>`
2. **Do not just code it, test it yourself with a screen reader!** Most screen readers have Speech Viewer that prints page content instead of saying it which makes testing more convenient.
3. Establish your patterns early during development, less effort up-front than retro fitting later.
4. All page functionality is available using the keyboard - ensure all page elements including text support sequential keyboard navigation (usually with the **Tab** key).
5. Each page must have a descriptive and informative page title that is displayed in the browser tab.

## Implementation Patterns

### Tab Indexing

1. Assign tabindex to "0" for controls that needs to be included in tab index.
1. Assign tabindex to "-1" for controls that needs to be excluded from tab index.

### Dynamically Displayed Content

Screen readers need to be notified when new content/forms are dynamically displayed:

1. (AngularJS) Avoid `[hidden]="expression"` use `*ngIf="expression"` instead.  Screen readers tend to read hidden elements.
1. For errors, announce revealed content with `role="alert" aria-live="assertive"`
1. If revealing new for element use  `role="dialogue"`
1. If you have multiple errors, wrap a `<div role="alert" aria-live="assertive">` around all the messages


### Radio Buttons or Group of fields with a single label 

1. Use `<label for="">` for the first radio control
1. Use a hidden label `<label class="visuallyhidden" for="">` for the second and so on controls
 
 ```
/*
  Special accessibility class to hide things like labels but still have the readable by screen readers
 */
.visuallyhidden {
  position: absolute;
  overflow: hidden;
  clip: rect(0 0 0 0);
  height: 1px; width: 1px;
  margin: -1px; padding: 0; border: 0;
}
```
### Descriptions for all page elements

1. All images, form image buttons,  and image map hot spots have appropriate, equivalent alternative text (alt="<description>").
2. Images that do not convey content, are decorative, or with content that is already conveyed in text, are given null alt text (alt="""") or implemented as CSS backgrounds. 'All  linked images have descriptive alternative text'.
3. Equivalent alternatives to complex images are provided in context or on a separate (linked and/or referenced via longdesc) page.
4. Form buttons have a descriptive value. Form inputs have associated text labels or, if labels cannot be used, a descriptive title attribute.
5. Embedded multimedia is identified via accessible text.

### Use of Color

1. Use Colour Contrast Checker tool to ensure an adequate color contrast ratio is maintained on all pages.
2. Do not use color as the sole method of conveying content or distinguishing visual elements such as links. Colour alone is not used to distinguish links from surrounding text unless the luminance contrast between the link and the surrounding text is at least 3:1 and **an additional differentiation (e.g., it becomes underlined) is provided when the link is hovered over or receives focus**.

### Multi-lingual support

1. In order to be supported by screen reader, the language of the page must be identified using the HTML lang attribute (<html lang="en">, for example).


### Input Assistance

1. Required form elements or form elements that require a specific format, value, or length provide this information within the element's label (or if a label is not provided, within the element's title attribute).
