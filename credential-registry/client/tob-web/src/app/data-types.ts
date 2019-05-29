import { BehaviorSubject } from 'rxjs/BehaviorSubject';
import { Observable } from 'rxjs';
import { Subscription } from 'rxjs/Subscription';
import { map } from 'rxjs/operators';

function load_data<T>(
    obj: T,
    result: any,
    attr_map?: {[key: string]: any},
    list_map?: {[key: string]: any}): T {
  if(obj && result) {
    for(let k in result) {
      if(attr_map && k in attr_map) {
        obj[k] = (result[k] === null || result[k] === undefined)
          ? null : (new Model[attr_map[k]])._load(result[k]);
      }
      else if(list_map && k in list_map) {
        obj[k] = (result[k] === null || result[k] === undefined)
          ? [] : result[k].map((v) => (new Model[list_map[k]])._load(v));
      }
      else {
        obj[k] = result[k];
      }
    }
  }
  return obj;
}


export namespace Model {

  export interface ModelCtor<M extends BaseModel> {
    new (value?: any): M;
    propertyMap: {[key: string]: string};
    listPropertyMap: {[key: string]: string};
    resourceName: string;
    childResource: string;
    extPath: string;
  }

  export abstract class BaseModel {
    static propertyMap: {[key: string]: string} = {};
    static listPropertyMap: {[key: string]: string} = {};
    static resourceName: string;
    static childResource: string;
    static extPath: string;

    constructor(data?: any) {
      if(data) {
        this._load(data);
      }
    }

    _load<T extends BaseModel>(result: any) {
      let ctor = (this.constructor as ModelCtor<T>);
      return load_data(this, result, ctor.propertyMap, ctor.listPropertyMap);
    }

    get pageTitle(): string {
      return null;
    }

    get json(): string {
      return JSON.stringify(this, null, 2);
    }
  }

  function mapByType<T extends {type: string}>(input: T[]): {[key: string]: T} {
    let result = {};
    if(input) {
      for(let obj of input) {
        result[obj.type] = obj;
      }
    }
    return result;
  }

  function setCredTypeId(attrs: Attribute[], credType: CredentialType) {
    let credTypeId = credType && credType.id;
    for(let i = 0; attrs && i < attrs.length; i++)
      attrs[i].credential_type_id = credTypeId;
  }

  export class Address extends BaseModel {
    id: number;
    addressee: string;
    civic_address: string;
    city: string;
    province: string;
    postal_code: string;
    country: string;
    address_type: string;
    credential_id: number;
    inactive: boolean;

    static resourceName = 'address';
  }

  export class Attribute extends BaseModel {
    id: number;
    type: string;
    format: string;
    value: string;
    credential_id: number;
    credential_type_id: number;
    inactive: boolean;

    get typeClass(): string {
      if(this.format === 'email' || this.format === 'phone' || this.format === 'name')
        return this.format;
      if(this.format === 'url')
        return 'website';
    }

    get typeLabel(): string {
      if(this.type && ! ~this.type.indexOf('.'))
        return `attribute.${this.type}`;
      return this.type;
    }
  }

  export class Credential extends BaseModel {
    id: number;
    credential_type: CredentialType;
    credential_set: CredentialSet;
    effective_date: string;
    inactive: boolean;
    latest: boolean;
    revoked: boolean;
    revoked_date: string;
    last_issue_date: string;

    addresses: Address[];
    _attributes: Attribute[];
    _attribute_map: {[key: string]: Attribute};
    names: Name[];
    local_name: Name;
    remote_name: Name;
    topic: Topic;
    related_topics: Topic[];

    get pageTitle(): string {
      return this.credential_type && this.credential_type.description;
    }

    static resourceName = 'credential';

    static propertyMap = {
      credential_type: 'CredentialType',
      credential_set: 'CredentialSet',
      topic: 'Topic',
    };
    static listPropertyMap = {
      addresses: 'Address',
      attributes: 'Attribute',
      names: 'Name',
      related_topics: 'Topic',
    };

    get attributes(): Attribute[] {
      return this._attributes;
    }
    set attributes(attrs: Attribute[]) {
      setCredTypeId(attrs, this.credential_type);
      this._attributes = attrs;
      this._attribute_map = mapByType(this._attributes);
    }

    get attribute_map(): {[key: string]: Attribute} {
      return this._attribute_map || {};
    }

    get issuer(): Issuer {
      return this.credential_type && this.credential_type.issuer;
    }
    set issuer(val: Issuer) {
    }
    get haveAddresses() {
      return this.topic.addresses && this.topic.addresses.length;
    }
    get haveAttributes() {
      return this.attributes && this.attributes.length;
    }
    get haveNames() {
      return this.names && this.names.length;
    }

    get relatedPreferredName() : string {
      let found = '';
      if('associated_registration_name' in this.attribute_map) {
        let attr = this.attribute_map['associated_registration_name'];
        return attr.value;
      }
      if(0 < this.related_topics.length) {
        if(0 < this.related_topics[0].names.length) {
          for(let name of this.related_topics[0].names) {
            if(name.type === 'entity_name_assumed') {
              found = name.text;
            }
          }
          if(! found) {
            found = this.related_topics[0].names[0].text;
          }
        }
      }
      return found;
    }

    get link() {
      if(this.topic) {
        return this.topic.link.concat(['/cred/', ''+this.id]);
      }
    }
  }

  export class CredentialFormatted extends Credential {
    static extPath = 'formatted';
  }

  export class CredentialSearchResult extends Credential {
    static resourceName = 'search/credential/topic';
  }

  export class CredentialFacetSearchResult extends Credential {
    static resourceName = 'search/credential/topic/facets';
  }

  export class CredentialVerifyResult extends BaseModel {
    success: boolean;
    result: any;

    static resourceName = 'credential';
    static extPath = 'verify';

    get claims() {
      let ret = [];
      if(typeof this.result === 'object' && this.result.proof) {
        let attrs = this.result.proof.requested_proof.revealed_attrs;
        for(let k in attrs) {
          ret.push({name: k, value: attrs[k].raw});
        }
      }
      ret.sort((a,b) => a.name.localeCompare(b.name));
      return ret;
    }

    get status(): string {
      return this.success ? 'cred.verified' : 'cred.not-verified';
    }

    get text(): string {
      if(typeof this.result === 'string')
        return this.result;
      return JSON.stringify(this.result, null, 2);
    }
  }

  export class CredentialSet extends BaseModel {
    id: number;
    credentials: Credential[];
    credential_type: CredentialType;
    latest_credential: Credential;
    latest_credential_id: number;
    first_effective_date: string;
    last_effective_date: string;

    static propertyMap = {
      latest_credential: 'Credential',
      credential_type: 'CredentialType',
      topic: 'Topic',
    };
    static listPropertyMap = {
      credentials: 'Credential',
    };

    static resourceName = 'topic';
    static childResource = 'credentialset';
  }

  export class CredentialType extends BaseModel {
    id: number;
    // schema: Schema;
    issuer: Issuer;
    description: string;
    // processorConfig: string;
    credential_def_id: string;
    // visible_fields: string;
    has_logo: boolean;

    static resourceName = 'credentialtype';

    static propertyMap = {
      issuer: 'Issuer',
    };

    get logo_url(): string {
      if(this.has_logo) {
        return `${CredentialType.resourceName}/${this.id}/logo`;
      }
    }
  }

  export class Issuer extends BaseModel {
    id: number;
    did: string;
    name: string;
    abbreviation: string;
    email: string;
    url: string;
    has_logo: boolean;

    static resourceName = 'issuer';

    get pageTitle(): string {
      return this.name;
    }

    get logo_url(): string {
      if(this.has_logo) {
        return `${Issuer.resourceName}/${this.id}/logo`;
      }
    }
  }

  export class IssuerCredentialType extends CredentialType {
    static resourceName = 'issuer';
    static childResource = 'credentialtype';
  }

  export class Name extends BaseModel {
    id: number;
    text: string;
    type: string;
    credential_id: number;
    inactive: boolean;

    static resourceName = 'name';

    // extra API fields
    issuer: Issuer;
    static propertyMap = {
      issuer: 'Issuer',
    };
  }

  export class Topic extends BaseModel {
    id: number;
    source_id: string;
    type: string;

    addresses: Address[];
    _attributes: Attribute[];
    _attribute_map: {[key: string]: Attribute};
    names: Name[];
    local_name: Name;
    remote_name: Name;

    static resourceName = 'topic';

    static listPropertyMap = {
      addresses: 'Address',
      attributes: 'Attribute',
      names: 'Name',
    };

    get attributes(): Attribute[] {
      return this._attributes;
    }
    set attributes(attrs: Attribute[]) {
      this._attributes = attrs;
      this._attribute_map = mapByType(this._attributes);
    }

    get attribute_map(): {[key: string]: Attribute} {
      return this._attribute_map || {};
    }

    get pageTitle(): string {
      if(this.names && this.names.length) {
        return this.names[0].text;
      }
    }

    get preferredName(): Name {
      let found = null;
      if(this.names) {
        for(let name of this.names) {
          if(name.type === 'entity_name_assumed')
            found = name;
        }
        if(! found)
          found = this.names[0];
      }
      return found;
    }

    get localName(): Name {
      return this.preferredName;
    }

    get remoteName(): Name {
      let p_name = this.preferredName;
      if (p_name.type === 'entity_name_assumed') {
        if(this.names) {
          for(let name of this.names) {
            if(name.type != 'entity_name_assumed') {
              return name;
            }
          }
        }
      }
      return null;
    }

    get typeLabel(): string {
      if(this.type) return ('name.'+this.type).replace(/_/g, '-');
      return '';
    }

    get link(): string[] {
      // FIXME need to move link generation into general data service
      if(this.type === 'registration')
        return ['/topic/', this.source_id];
      return ['/topic/', this.type, this.source_id];
    }

    extLink(...args): string[] {
      return this.link.concat(args)
    }
  }

  export class TopicFormatted extends Topic {
    static extPath = 'formatted';
  }

  export class TopicRelatedFrom extends Topic {
    static childResource = 'related_from';
  }

  export class TopicRelatedTo extends Topic {
    static childResource = 'related_to';
  }

  export class TopicRelationship extends BaseModel {
    topic_id: number;
    relation_id: number;
    credential: Credential;
    topic: Topic;
    related_topic: Topic;
    relation_type = 'to';

    _attributes: Attribute[];
    _attribute_map: {[key: string]: Attribute};

    static resourceName = 'topic_relationship';

    get attributes(): Attribute[] {
      return this._attributes;
    }
    set attributes(attrs: Attribute[]) {
      this._attributes = attrs;
      this._attribute_map = mapByType(this._attributes);
    }

    get attribute_map(): {[key: string]: Attribute} {
      return this._attribute_map || {};
    }

    get other_topic() : Topic {
      if (this.relation_type == 'to') {
        return this.related_topic;
      } else {
        return this.topic;
      }
    }

    get preferredName() : Name {
      let found = null;
      if('associated_registration_name' in this._attribute_map) {
        let attr = this._attribute_map['associated_registration_name'];
        let name = new Name({
          id: this.credential.id,
          text: attr.value,
          type: 'Associated Registration',
          credential_id: this.credential.id,
          inactive: false,
          issuer: this.credential.credential_type.issuer}
        );
        return name;
      }
      let other = this.other_topic;
      if(other.names) {
        for(let name of other.names) {
          if(name.type === 'entity_name_assumed')
            found = name;
        }
        if(! found)
          found = other.names[0];
      }
      return found;
    }

    get link() : string[] {
      // FIXME need to move link generation into general data service
      let other = this.other_topic;
      if(other.type === 'registration')
        return ['/topic/', other.source_id];
      return ['/topic/', other.type, other.source_id];
    }

    get typeLabel() : string {
      let other = this.other_topic;
      if(other.type) return ('name.'+other.type).replace(/_/g, '-');
      return '';
    }

    get relationLabel() : string {
      return this._attribute_map['relationship_description'].value;
    }

    get otherEntityStatus() : Attribute {
      let other = this.other_topic;
      let other_attribute_map = mapByType(other.attributes);
      return other_attribute_map['entity_status'];
    }

    get otherEntityType() : Attribute {
      let other = this.other_topic;
      let other_attribute_map = mapByType(other.attributes);
      return other_attribute_map['entity_type'];
    }
  }

  export class TopicRelationshipRelatedFrom extends TopicRelationship {
    static childResource = 'related_from_relations';
    relation_type = 'from';
  }

  export class TopicRelationshipRelatedTo extends TopicRelationship {
    static childResource = 'related_to_relations';
    relation_type = 'to';
  }

}
// end Model


export namespace Fetch {

  export class BaseResult<T> {
    public data: T;
    public meta: any;
    protected _input: any;

    constructor(
        protected _ctor: (any) => T,
        input?: any,
        public error?: any,
        public loading: boolean = false,
        meta = null) {
      this.input = input;
      this.meta = meta || {};
    }

    get input(): any {
      return this._input;
    }

    set input(value: any) {
      this._input = value;
      this.data = value ? this._ctor(value) : null;
    }

    get empty(): boolean {
      return ! this.data;
    }

    get loaded(): boolean {
      return !! this.data;
    }

    get notFound(): boolean {
      return this.error && this.error.obj && this.error.obj.status === 404;
    }
  }

  export class ListInfo {
    public pageNum: number = 1;
    public pageCount: number = 0;
    public resultCount: number = 0;
    public totalCount: number = 0;
    public firstIndex = 0;
    public lastIndex = 0;
    public timing: number = 0;
    public previous: string = null;
    public next: string = null;
    public params: {[key: string]: any};
    public facets: any;

    get havePrevious(): boolean {
      return this.previous != null;
    }

    get haveNext(): boolean {
      return this.next != null;
    }

    static fromResult(value: any, facets?: any): ListInfo {
      let ret = new ListInfo();
      ret.facets = facets;
      if(value) {
        ret.pageNum = value.page || null;
        ret.firstIndex = value.first_index || null;
        ret.lastIndex = value.last_index || null;
        ret.totalCount = value.total || null;
        ret.next = value.next || null;
        ret.previous = value.previous || null;
      }
      return ret;
    }
  }

  export class ListResult<T> extends BaseResult<T[]> {
    public info: ListInfo;

    get input(): any {
      return this._input;
    }

    set input(value: any) {
      this._input = value;
      if(value instanceof Array) {
        this.data = this._ctor(value);
      }
      else if(value && 'results' in value && value['results'] instanceof Array) {
        this.data = this._ctor(value['results']);
        this.info = ListInfo.fromResult(value);
      }
      else if(value && 'objects' in value) {
        this.data = this._ctor(value['objects']['results']);
        this.info = ListInfo.fromResult(value['objects'], value['facets']);
      }
      else {
        this.data = null;
      }
    }
  }

  export interface ResultCtor<T, R extends BaseResult<T>> {
    new (
      ctor: (any) => T,
      input?: any,
      error?: any,
      loading?: boolean,
      meta?: any): R;
  }

  export class RequestParams {
    path?: string;
    resource?: string;
    recordId?: string;
    childResource?: string;
    childId?: string;
    extPath?: string;
    persist: boolean = false;

    static fromModel<M extends Model.BaseModel>(ctor: Model.ModelCtor<M>) {
      let req = new RequestParams();
      req.resource = ctor.resourceName;
      req.childResource = ctor.childResource;
      req.extPath = ctor.extPath;
      return req;
    }

    static from(params: any) {
      let req = new RequestParams();
      if(params)
        Object.assign(req, params);
      return req;
    }

    extend(info: RequestParams | { [key: string]: any }) {
      let ret = new RequestParams();
      Object.assign(ret, this);
      if(info)
        Object.assign(ret, info);
      return ret;
    }

    getRecordPath(recordId?: string, childId?: string, extPath?: string): string {
      let path = null;
      if(this.path) {
        path = this.path;
      }
      else if(this.resource) {
        if(! recordId) recordId = this.recordId;
        if(! extPath) extPath = this.extPath;
        if(recordId) {
          path = `${this.resource}/${recordId}`;
          if(this.childResource) {
            if(! childId) childId = this.childId;
            if(childId)
              path = `${path}/${this.childResource}/${childId}`;
            else
              path = null;
          }
          else if(extPath) {
            path = `${path}/${extPath}`;
          }
        }
      }
      return path;
    }

    getListPath(recordId?: string, extPath?: string): string {
      let path = null;
      if(this.path) {
        path = this.path;
      }
      else if(this.resource) {
        if(! recordId) recordId = this.recordId;
        if(! extPath) extPath = this.extPath;
        path = this.resource;
        if(this.childResource) {
          if(recordId)
            path = `${path}/${recordId}/${this.childResource}`;
          else
            path = null;
        }
        else if(extPath) {
          path = `${path}/${extPath}`;
        }
      }
      return path;
    }
  }

  export class BaseLoader<T, R extends BaseResult<T>> {
    _postProc = [];
    _result: BehaviorSubject<R>;
    _sub: Subscription;

    constructor(
      protected _rctor: ResultCtor<T, R>,
      protected _map: (any) => T,
      protected _req?: RequestParams
    ) {
      if(! this._req) this._req = new RequestParams();
      this._result = new BehaviorSubject(this._makeResult());
    }

    complete() {
      this._clearSub();
      if(this._result) {
        this._result.complete();
        this._result = null;
      }
    }

    reset() {
      this._clearSub();
      this.result = this._makeResult();
    }

    _clearSub() {
      if(this._sub) {
        this._sub.unsubscribe();
        this._sub = null;
      }
    }

    protected _makeResult(input?: any, error?: any, loading: boolean = false, meta=null) {
      return new this._rctor(this._map, input, error, loading, meta);
    }

    postProc(hook) {
      this._postProc.push(hook);
    }

    get stream(): Observable<R> {
      return this._result.asObservable();
    }

    get ready(): Observable<R> {
      return this.stream.filter(result => result.loaded);
    }

    get result(): R {
      return this._result.value;
    }

    _runPostProc(val: R, pos = 0) {
      let proc = this._postProc[pos];
      let result = null;
      if(proc)
        result = proc(val);
      if(! result)
        result = Promise.resolve(val);
      else
        result = result.then(newval => this._runPostProc(newval, pos + 1));
      return result;
    }

    set result(val: R) {
      this._runPostProc(val).then((result) => {
        this._result.next(result);
      });
    }

    get request(): RequestParams {
      return this._req;
    }

    loadData(input: any, meta = null) {
      this.result = this._makeResult(input, null, false, meta);
    }

    loadError(err: any, meta = null) {
      this.result = this._makeResult(null, err, false, meta);
    }

    loadFrom(obs: Observable<any>, meta = null) {
      this._clearSub();
      let input = this._req.persist ? this.result.input : null;
      this.result = this._makeResult(input, null, true, meta);
      this._sub = obs.subscribe(
        (result) => this.loadData(result, meta),
        (err) => this.loadError(err, meta)
      );
    }

    loadNotFound(meta = null) {
      this.loadError({obj: {status: 404}});
    }
  }

  export class DataLoader<T> extends BaseLoader<T, BaseResult<T>> {
    constructor(
        map: (any) => T,
        req?: RequestParams) {
      super(BaseResult, map, req);
    }
  }

  export class JsonLoader extends DataLoader<any> {
    constructor(req?: RequestParams) {
      super(val => val, req);
    }
  }

  export class ListLoader<T> extends BaseLoader<T[], ListResult<T>> {
    constructor(
        protected _mapEntry: (any) => T,
        req?: RequestParams) {
      super(
        ListResult,
        data => {
          let list = null;
          if(data instanceof Array) {
            list = [];
            for(let row of data) {
              list.push(_mapEntry(row));
            }
          } else if(data) {
            console.error("Expected array");
          }
          return list;
        },
        req);
    }
  }

  export class ModelLoader<M extends Model.BaseModel> extends DataLoader<M> {
    constructor(ctor: Model.ModelCtor<M>, req?: RequestParams | { [key: string]: any }) {
      let creq = RequestParams.fromModel(ctor).extend(req);
      super((data) => new ctor(data), creq);
    }
  }

  export class ModelListLoader<M extends Model.BaseModel> extends ListLoader<M> {
    constructor(ctor: Model.ModelCtor<M>, req?: RequestParams | { [key: string]: any }) {
      let creq = RequestParams.fromModel(ctor).extend(req);
      super((data) => new ctor(data), creq);
    }
  }
}
// end Fetch


export namespace Filter {

  export interface Option {
    label?: string;
    tlabel?: string;
    value: string;
    active?: boolean;
    count?: number;
  }

  export interface FieldSpec {
    name: string;
    label?: string;
    alias?: string;
    options?: Option[];
    hidden?: boolean;
    defval?: string;
    value?: string;
    blank?: boolean;
  }

  export class Field implements FieldSpec {
    public id = '';
    public name = '';
    public alias = null;
    public label = '';
    public hidden = false;
    public defval = '';
    public blank = false;
    _options: any[];
    _value: string = null;

    constructor(init?: FieldSpec) {
      if(init) {
        Object.assign(this, init);
        this.options = init.options;
      }
    }

    clone() {
      return new Field(this);
    }

    get options() {
      return this._options;
    }

    set options(vals) {
      this._options = vals ? vals.map(o => Object.assign({}, o)) : [];
      for(let o of this._options) {
        if(! o.id) o.id = this.name + '_' + (o.value || 'blank');
      }
      this.setActive();
    }

    get value() {
      return this._value;
    }

    set value(val: string) {
      if(val === undefined || val === null) val = this.defval;
      this._value = val;
      this.setActive();
    }

    setActive() {
      let val = this.value;
      if(this._options) {
        for(let o of this._options) {
          o.active = (o.value === val);
        }
      }
    }
  }

  interface StrDict {[key: string]: string}

  export class FieldSet {
    _result: BehaviorSubject<Field[]>;
    _fields: Field[] = [];
    _defaults: StrDict = {};
    _values: StrDict = {};

    constructor(
      fields: FieldSpec[]
    ) {
      let fs = [];
      if(fields) {
        for(let opt of fields)
          fs.push(new Field(opt));
      }
      this._fields = fs;
      this._result = new BehaviorSubject(this._next());
    }

    loadQuery(params: StrDict) {
      let upd = {};
      for(let opt of this._fields) {
        let k = opt.alias || opt.name;
        if(k in params)
          upd[opt.name] = params[k];
      }
      this.update(upd);
    }

    get stream(): Observable<Field[]> {
      return this._result.asObservable();
    }

    get streamVisible(): Observable<Field[]> {
      return this.stream.pipe(map(fs => fs.filter(f => ! f.hidden)));
    }

    get result(): Field[] {
      return this._result.value;
    }

    get queryParams(): StrDict {
      let fs = this.result;
      let ret = {};
      for(let opt of fs) {
        if(opt.value !== null) {
          ret[opt.alias || opt.name] = opt.value;
        }
      }
      return ret;
    }

    complete() {
      if(this._result) {
        this._result.complete();
        this._result = null;
      }
    }

    reset() {
      this.values = {};
    }

    getFieldValue(key: string): string {
      return this._values[key];
    }

    setFieldValue(key: string, value: string|number) {
      let upd = {};
      upd[key] = value;
      this.update(upd);
    }

    setOptions(key: string, value: any) {
      for(let f of this._fields) {
        if(f.name === key) {
          f.options = value;
          this.update();
          break;
        }
      }
    }

    update(vals?: StrDict) {
      let v = {... this._values};
      if(vals)
        Object.assign(v, vals);
      this.values = v;
    }

    _next() {
      let vs = this._values;
      let fs = [];
      for(let f of this._fields) {
        let f2 = f.clone();
        f2.value = vs[f2.name];
        fs.push(f2);
      }
      return fs;
    }

    _update() {
      if(this._result)
        this._result.next(this._next());
    }

    get defaults() {
      return this._defaults;
    }

    set defaults(vals: StrDict) {
      this._defaults = vals || {};
      this.update();
    }

    get values() {
      return {... this._values};
    }

    set values(vals: StrDict) {
      let v = {};
      for(let f of this._fields) {
        let defval = f.defval;
        if(f.name in this._defaults)
          defval = this._defaults[f.name];
        if(vals && f.name in vals && vals[f.name] !== null) {
          let input = vals[f.name];
          if(typeof input === 'string' || typeof input === 'number') {
            input = ('' + input).trim();
          }
          if(input === '' && defval !== '' && ! f.blank) {
            input = defval;
          }
          v[f.name] = input;
        }
        else {
          v[f.name] = defval;
        }
      }
      this._values = v;
      this._update();
    }
  }
}
// end Filter
