frappe.ui.form.on('Supplier', {
    custom_add_brand: function (frm) {
        let selectedAssignees = frm.doc.brand
            ? frm.doc.brand.split(',').map(a => a.trim()).filter(Boolean)
            : [];

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Brand',
                fields: ['brand'],
                limit_page_length: 0,
            },
            callback: function (response) {
                if (response.message) {
                    let options = response.message.map(item => item.brand).filter(Boolean);

                    const dialog = new frappe.ui.Dialog({
                        title: __('Select Brand'),
                        fields: [
                            {
                                label: __("Select Brand"),
                                fieldtype: "MultiSelectList",
                                fieldname: "brand",
                                placeholder: "Select Brand",
                                options: options,
                                reqd: 1,
                                get_data: function () {
                                    return options.map(brand => ({
                                        value: brand,
                                        description: ""
                                    }));
                                }
                            }
                        ],
                        primary_action_label: __('Submit'),
                        primary_action: function (values) {
                            let newAssignees = values['brand'] || [];
                            let duplicates = newAssignees.filter(brand => selectedAssignees.includes(brand));

                            if (duplicates.length > 0) {
                                frappe.msgprint(
                                    __("The following brands are already selected: {0}.", [duplicates.join(', ')])
                                );
                            } else {
                                selectedAssignees = [...new Set([...selectedAssignees, ...newAssignees])];
                                frm.set_value("custom_brand", selectedAssignees.join(', '));
                                frm.refresh_field('brand');
                            }

                            dialog.hide();
                            $('body').removeClass('modal-open');
                        }
                    });

                    dialog.show();
                    $('body').addClass('modal-open');

                    let userCount = options.length;
                    let dynamicHeight = userCount * 100;
                    if (userCount > 10) {
                        dynamicHeight = 300;
                    }

                    dialog.$wrapper.find('.modal-body').css({
                        "overflow-y": "auto",
                        "height": dynamicHeight + "px",
                        "max-height": "90vh"
                    });
                } else {
                    frappe.msgprint(__('No brands found.'));
                }
            }
        });
    }
});


















