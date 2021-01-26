from app import db

class ModuleCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    nioicon = db.Column(db.String(200))
    modules = db.relationship('Module', backref='parent', lazy='dynamic')

    @staticmethod
    def insert_categories():
        category = ModuleCategory.query.first()
        if category is None:
            categories = [
                ModuleCategory(name='Sales', nioicon='<em class="icon ni ni-report-profit"></em>'),
                ModuleCategory(name='Services', nioicon='<em class="icon ni ni-coffee-fill"></em>'),
                ModuleCategory(name='Accounting', nioicon='<em class="icon ni ni-coins"></em>'),
                ModuleCategory(name='Inventory', nioicon='<em class="icon ni ni-box"></em>'),
                ModuleCategory(name='Manufacturing', nioicon='<em class="icon ni ni-setting"></em>'),
                ModuleCategory(name='Marketing', nioicon='<em class="icon ni ni-share-alt"></em>'),
                ModuleCategory(name='Human Resources', nioicon='<em class="icon ni ni-users"></em>'),
                ModuleCategory(name='Productivity', nioicon='<em class="icon ni ni-layers"></em>'),
                ModuleCategory(name='Administration', nioicon='<em class="icon ni ni-archived"></em>'),
            ]
        db.session.bulk_save_objects(categories)
        db.session.commit()
    

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('module_category.id'))
    category = db.relationship('ModuleCategory', backref='categories')
    short_description = db.Column(db.String(200))
    description = db.Column(db.Text)
    svg_description = db.Column(db.Text())

    @staticmethod
    def insert_modules():
        module = Module.query.first()
        if module is None:
            modules = [
                Module(name='Sales', short_description='From quotations to invoices', category_id=1, svg_description='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 90"><path d="M68.14,80.86,30.21,72.69a5.93,5.93,0,0,1-4.57-7l12.26-56A6,6,0,0,1,45,5.14l28.18,6.07L85.5,29.51,75.24,76.33A6,6,0,0,1,68.14,80.86Z" fill="#eff1ff" stroke="#6576ff" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><polyline points="73 12.18 69.83 26.66 85.37 30.08" fill="#eff1ff" stroke="#6576ff" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><path d="M66.26,71.15,29.05,82.46a6,6,0,0,1-7.46-4L4.76,23.15a6,6,0,0,1,4-7.47l27.64-8.4L56.16,17.39,70.24,63.68A6,6,0,0,1,66.26,71.15Z" fill="#e3e7fe" stroke="#6576ff" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><polyline points="36.7 8.22 41.05 22.53 56.33 17.96" fill="#e3e7fe" stroke="#6576ff" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><path d="M68,85H29a6,6,0,0,1-6-6V21a6,6,0,0,1,6-6H58L74,30.47V79A6,6,0,0,1,68,85Z" fill="#fff" stroke="#6576ff" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><polyline points="58 16 58 31 74 31.07" fill="#fff" stroke="#6576ff" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><line x1="45" y1="41" x2="61" y2="41" fill="none" stroke="#c4cefe" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><line x1="35" y1="48" x2="61" y2="48" fill="none" stroke="#c4cefe" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><line x1="35" y1="55" x2="61" y2="55" fill="none" stroke="#c4cefe" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><line x1="35" y1="63" x2="61" y2="63" fill="none" stroke="#c4cefe" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><line x1="35" y1="69" x2="51" y2="69" fill="none" stroke="#c4cefe" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><text transform="translate(34.54 43.18) scale(0.99 1)" font-size="9.31" fill="#6576ff" font-family="Nunito-Black, Nunito Black">$</text></svg>'),

                Module(name='CRM', short_description='Track leads and close opportunities', category_id=1, svg_description='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 90"><path d="M68.14,80.86,30.21,72.69a5.93,5.93,0,0,1-4.57-7l12.26-56A6,6,0,0,1,45,5.14l28.18,6.07L85.5,29.51,75.24,76.33A6,6,0,0,1,68.14,80.86Z" fill="#eff1ff" stroke="#6576ff" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><polyline points="73 12.18 69.83 26.66 85.37 30.08" fill="#eff1ff" stroke="#6576ff" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><path d="M66.26,71.15,29.05,82.46a6,6,0,0,1-7.46-4L4.76,23.15a6,6,0,0,1,4-7.47l27.64-8.4L56.16,17.39,70.24,63.68A6,6,0,0,1,66.26,71.15Z" fill="#e3e7fe" stroke="#6576ff" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><polyline points="36.7 8.22 41.05 22.53 56.33 17.96" fill="#e3e7fe" stroke="#6576ff" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><path d="M68,85H29a6,6,0,0,1-6-6V21a6,6,0,0,1,6-6H58L74,30.47V79A6,6,0,0,1,68,85Z" fill="#fff" stroke="#6576ff" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><polyline points="58 16 58 31 74 31.07" fill="#fff" stroke="#6576ff" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><line x1="45" y1="41" x2="61" y2="41" fill="none" stroke="#c4cefe" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><line x1="35" y1="48" x2="61" y2="48" fill="none" stroke="#c4cefe" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><line x1="35" y1="55" x2="61" y2="55" fill="none" stroke="#c4cefe" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><line x1="35" y1="63" x2="61" y2="63" fill="none" stroke="#c4cefe" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><line x1="35" y1="69" x2="51" y2="69" fill="none" stroke="#c4cefe" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" /><text transform="translate(34.54 43.18) scale(0.99 1)" font-size="9.31" fill="#6576ff" font-family="Nunito-Black, Nunito Black">$</text></svg>')                
            ]
        db.session.bulk_save_objects(modules)
        db.session.commit()


    

