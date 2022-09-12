frappe.ui.form.on('Attendance',  {
    validate: function(frm) {
        if(frappe.user_roles.includes('Employee Checkin')) {
            //msgprint('You are only allowed Checkin');
            frm.set_df_property('attendance_date', 'read_only', 1);
            if (frm.doc.in) {
                frm.set_df_property('start_time', 'read_only', 1);
                frm.set_df_property('in', 'read_only', 1);

            }
            if (frm.doc.out) {
                frm.set_df_property('end_time', 'read_only', 1);
                frm.set_value('end_time', frappe.datetime.now_time());
                frm.set_df_property('out', 'read_only', 1);

            }
            //validated = false;
        }
        if(frappe.session.user === 'Administrator') {
            //msgprint('You are only allowed edit doc');
            frm.set_df_property('start_time', 'read_only', 0);
            frm.set_df_property('in', 'read_only', 0);
            frm.set_df_property('end_time', 'read_only', 0);
            frm.set_df_property('out', 'read_only', 0);
            //validated = true;
        }

    },
    refresh:function(frm){
    if(frm.doc.shift)
        {
            console.log("&&&&&&&&&in shift&&&&",cur_frm.doc.shift);
            if(frm.doc.shift)
            {
                frappe.call({
                        method: 'chemtech_custom_app.chemtech.custom_script.attendance.get_shift_time_detail',
                        args: {
                            //shift: frm.doc.shift,
                            start_time:cur_frm.doc.start_time,
                            doc:cur_frm.doc
                        },
                        callback:function(r){
                            if(r.message)                            
                            {
                                console.log(r)
                                cur_frm.set_value("early_by",r.message[0]);

                                console.log("in early_by",cur_frm.doc.early_by)
                                cur_frm.set_value("late_by",r.message[1]);
                                console.log("in late_by",cur_frm.doc.late_by)
                                //refresh_field("early_by");
                            
                            }
                        }
                    });
            }
        }
    }
});
