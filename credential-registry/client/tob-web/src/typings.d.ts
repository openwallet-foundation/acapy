/* Allow JSON files to be dynamically imported
   Note: typescript 2.9 adds resolveJsonModule compiler option instead
*/
declare module "*.json" {
    const value: any;
    export default value;
}
