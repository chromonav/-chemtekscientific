frappe.listview_settings['Supplier'] = {
    onload: function (listview) {
        listview.page.add_field({
            fieldname: 'custom_brand',
            label: __('Brand'),
            fieldtype: 'MultiSelectList',
            options: 'Brand',
            get_data: function () {
                return frappe.db.get_link_options('Brand');
            },
            change: function () {
                const selected_values = listview.page.fields_dict.custom_brand.get_value();

                if (selected_values && selected_values.length > 0) {
                    frappe.call({
                        method: 'frappe.client.get_list',
                        args: {
                            doctype: 'Supplier',
                            fields: ['name', 'custom_brand'],
                            limit_page_length: 0 
                        },
                        callback: function (response) {
                            if (response.message && response.message.length > 0) {
                                let filteredNames = response.message
                                    .filter(doc => {
                                        const brands_in_doc = doc.custom_brand.split(',').map(b => b.trim());
                                        return selected_values.every(brand => brands_in_doc.includes(brand));
                                    })
                                    .map(doc => doc.name);
                                
                                if (filteredNames.length > 0) {
                                    listview.filter_area.clear('name'); 
                                    listview.filter_area.add([
                                        ['Supplier', 'name', 'in', filteredNames]
                                    ]);
                                    listview.refresh(); 
                                } else {
                                    listview.filter_area.clear('name');
                                    listview.refresh();
                                }
                            }
                        },
                    });
                } else {
                    listview.filter_area.clear('name');
                    listview.refresh();
                }
            }
        });
    }
};
