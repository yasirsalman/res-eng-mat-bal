# insert directory where libraries exits
import sys
sys.path.insert(1,'./')

import libraries.main as main
import pandas as pd
import os
import datetime
import libraries.plots as plots
from flask import Flask, render_template, request
from plotly.offline import plot
import json
import plotly
from libraries.main2 import tank as tank_instance


regress = False
regress_config = None

path = os.path.dirname(__name__)
file = os.path.join(path, '../data/lsu_matbal/OilMBEx.xls')
keep_cols = ['Days', 'Np\nSTBO', 'Gp\nMCF', 'Wp\nSTBW', 'Meas P\npsia']
df_prod = pd.read_excel(file, sheet_name='Calculations', skiprows=12, nrows=73)
df_prod.rename(columns={'Np\nSTBO': 'np', 'Gp\nMCF': 'gp', 'Wp\nSTBW': 'wp', 'Meas P\npsia': 'pressure'}, inplace=True)
startdate = datetime.date(2010, 1, 1)
df_prod['datestamp'] = [datetime.timedelta(day)+startdate for day in df_prod['Days']]
df_prod['wi'] = 0
df_prod['gi'] = 0
df_prod['gp'] = df_prod['gp']*1000.0
keep_cols = ['Pressure\npsia', 'Bo\nrb/stbo', 'Rs\nscf/stbo', 'Bg rb/mcf', 'Bt rb/stbo']
df_pvt_o = pd.read_excel(file, sheet_name='Oil PVT', skiprows=3, nrows=16)
df_pvt_o.rename(columns={'Pressure\npsia': 'pressure', 'Bo\nrb/stbo': 'oil_fvf', 'Rs\nscf/stbo': 'solution_gas'}, inplace=True)
keep_cols = ['Pressure psia', 'z', 'Bg\nrb/mcf']
df_pvt_g = pd.read_excel(file, sheet_name='Z Factors', skiprows=3, nrows=12)
df_pvt_g.rename(columns={'Pressure\npsia': 'pressure', 'Bg\nrb/mcf': 'gas_fvf'}, inplace=True)
tank = {
    'initial_inplace': 13.8E6,
    'initial_gascap': 0,
    'initial_pressure': 10180,
    'wei': 141.8e6,
    'J': 0.93,
    'swi': 0.2,
    'cw': 2.5e-6,
    'cf': 3e-5,
    'Boi': 1.735,
    'Bgi': 0.6508
}
pvt_master = {
    'gor': 1720,
    'sat_press': 8227,
    'temperature': 219,
}

def Run():
    tank1 = tank_instance()
    tank1.tank_data = tank
    tank1.prod_table = df_prod
    tank1.oil_pvt_table = df_pvt_o
    tank1.gas_pvt_table = df_pvt_g
    tank1.pvt_master = pvt_master
    tank1.regress = False
    tank1.regress_config = None
    ts_res, tank_results = tank1.matbal_run()

    # Dashboard
    plot1 = plots.plot_pressure_match(ts_res['Time'], ts_res['Calculated Pressure'], df_prod['Days'],
                                      df_prod['pressure'])
    plot1 = json.dumps(plot1, cls=plotly.utils.PlotlyJSONEncoder)
    plot2 = plots.plot_drive_indices(ts_res['Time'], ts_res['Depletion Drive Index'], ts_res['Segregation Drive Index'],
                                     ts_res['Water Drive Index'], ts_res['Compaction Drive Index'])
    plot2 = json.dumps(plot2, cls=plotly.utils.PlotlyJSONEncoder)
    return plot1, plot2, ts_res


app = Flask(__name__)


@app.route("/")
def template_start():
    plot1, plot2, df = Run()
    return render_template('template.html', plot1=plot1, plot2=plot2,
                           N=tank['initial_inplace'], Wei=tank['wei'], PI=tank['J'],
                           tables=[df.to_html(classes='data')], titles=df.columns.values)


@app.route("/recalc", methods=['GET'])
def template_recalc():
    test = request.args.get('N')
    tank['initial_inplace'] = request.args.get('N')
    tank['wei'] = request.args.get('Wei')
    tank['J'] = request.args.get('PI')
    plot1, plot2, df = Run()
    return { 'plot1':plot1, 'plot2':plot2,
            'N':tank['initial_inplace'], 'Wei':tank['wei'], 'PI':tank['J'],
            'tables':[df.to_html(classes='data')], 'titles':df.columns.values}


if __name__ == '__main__':
    app.run(debug=True)
