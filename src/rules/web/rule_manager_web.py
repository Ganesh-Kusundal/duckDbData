#!/usr/bin/env python3
"""
Rule Manager Web Interface

A simple web interface for rule management using Flask:
- View all rules in a dashboard
- Create new rules with forms
- Edit existing rules
- Validate rules
- Monitor performance
- Deploy rules to environments
"""

import json
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ..engine.rule_engine import RuleEngine
from ..validation.enhanced_validator import EnhancedRuleValidator
from ..templates.breakout_rules import BreakoutRuleTemplates
from ..templates.crp_rules import CRPRuleTemplates

app = Flask(__name__)
app.secret_key = 'rule-manager-secret-key-2025'

# Initialize components
rule_engine = RuleEngine()
validator = EnhancedRuleValidator(rule_engine)

# In-memory storage for demo (would be database in production)
rules_db = {}
rule_history = []

# Load initial rules
def load_initial_rules():
    """Load initial rule templates."""
    global rules_db

    # Load breakout rules
    breakout_rules = BreakoutRuleTemplates.get_all_templates()
    for rule in breakout_rules:
        rules_db[rule['rule_id']] = rule

    # Load CRP rules
    crp_rules = CRPRuleTemplates.get_all_templates()
    for rule in crp_rules:
        rules_db[rule['rule_id']] = rule

    print(f"Loaded {len(rules_db)} initial rules")

load_initial_rules()

@app.route('/')
def dashboard():
    """Main dashboard showing all rules."""
    rules_list = list(rules_db.values())
    total_rules = len(rules_list)
    active_rules = len([r for r in rules_list if r.get('enabled', True)])
    validated_rules = len([r for r in rules_list if validator.validate_single_rule_comprehensive(r).is_valid])

    # Recent activity
    recent_activity = rule_history[-5:] if len(rule_history) > 5 else rule_history

    return render_template('dashboard.html',
                         rules=rules_list,
                         total_rules=total_rules,
                         active_rules=active_rules,
                         validated_rules=validated_rules,
                         recent_activity=recent_activity)

@app.route('/rules')
def list_rules():
    """List all rules with filtering options."""
    rule_type = request.args.get('type', 'all')
    status = request.args.get('status', 'all')

    rules_list = list(rules_db.values())

    # Apply filters
    if rule_type != 'all':
        rules_list = [r for r in rules_list if r.get('rule_type') == rule_type]

    if status != 'all':
        if status == 'enabled':
            rules_list = [r for r in rules_list if r.get('enabled', True)]
        elif status == 'disabled':
            rules_list = [r for r in rules_list if not r.get('enabled', True)]

    return render_template('rules.html',
                         rules=rules_list,
                         current_type=rule_type,
                         current_status=status)

@app.route('/rules/<rule_id>')
def view_rule(rule_id):
    """View detailed rule information."""
    if rule_id not in rules_db:
        flash('Rule not found', 'error')
        return redirect(url_for('list_rules'))

    rule = rules_db[rule_id]

    # Get validation results
    validation_result = validator.validate_single_rule_comprehensive(rule)

    # Mock performance data (would come from monitoring system)
    performance_data = {
        'total_signals': 45,
        'successful_trades': 32,
        'win_rate': 71.1,
        'avg_profit': 2.3,
        'avg_loss': -1.8,
        'profit_factor': 1.9,
        'last_updated': datetime.now().isoformat()
    }

    return render_template('rule_detail.html',
                         rule=rule,
                         validation=validation_result,
                         performance=performance_data)

@app.route('/rules/create', methods=['GET', 'POST'])
def create_rule():
    """Create a new rule."""
    if request.method == 'POST':
        try:
            rule_data = {
                'rule_id': request.form['rule_id'],
                'name': request.form['name'],
                'description': request.form['description'],
                'rule_type': request.form['rule_type'],
                'enabled': 'enabled' in request.form,
                'priority': int(request.form['priority']),
                'conditions': {
                    'time_window': {
                        'start': request.form['time_start'],
                        'end': request.form['time_end']
                    }
                },
                'actions': {
                    'signal_type': request.form['signal_type'],
                    'confidence_calculation': 'weighted_average'
                },
                'metadata': {
                    'author': request.form.get('author', 'web-interface'),
                    'created_at': datetime.now().isoformat(),
                    'version': '1.0.0'
                }
            }

            # Add rule-type specific conditions
            if request.form['rule_type'] == 'breakout':
                rule_data['conditions']['breakout_conditions'] = {
                    'min_volume_multiplier': float(request.form['volume_multiplier']),
                    'min_price_move_pct': float(request.form['price_move_pct'])
                }
                rule_data['conditions']['market_conditions'] = {
                    'min_price': float(request.form['min_price']),
                    'max_price': float(request.form['max_price'])
                }
            elif request.form['rule_type'] == 'crp':
                rule_data['conditions']['crp_conditions'] = {
                    'close_threshold_pct': float(request.form['close_threshold']),
                    'range_threshold_pct': float(request.form['range_threshold'])
                }

            # Validate the rule
            validation_result = validator.validate_single_rule_comprehensive(rule_data)

            if validation_result.is_valid:
                rules_db[rule_data['rule_id']] = rule_data
                rule_history.append({
                    'action': 'created',
                    'rule_id': rule_data['rule_id'],
                    'timestamp': datetime.now().isoformat()
                })
                flash('Rule created successfully!', 'success')
                return redirect(url_for('view_rule', rule_id=rule_data['rule_id']))
            else:
                flash('Rule validation failed. Please check the errors.', 'error')
                return render_template('create_rule.html',
                                     rule=rule_data,
                                     validation_errors=validation_result.errors)

        except Exception as e:
            flash(f'Error creating rule: {str(e)}', 'error')

    return render_template('create_rule.html')

@app.route('/rules/<rule_id>/edit', methods=['GET', 'POST'])
def edit_rule(rule_id):
    """Edit an existing rule."""
    if rule_id not in rules_db:
        flash('Rule not found', 'error')
        return redirect(url_for('list_rules'))

    if request.method == 'POST':
        try:
            # Update rule data (simplified for demo)
            rule = rules_db[rule_id]
            rule['name'] = request.form['name']
            rule['description'] = request.form['description']
            rule['enabled'] = 'enabled' in request.form
            rule['priority'] = int(request.form['priority'])

            # Validate updated rule
            validation_result = validator.validate_single_rule_comprehensive(rule)

            if validation_result.is_valid:
                rule_history.append({
                    'action': 'updated',
                    'rule_id': rule_id,
                    'timestamp': datetime.now().isoformat()
                })
                flash('Rule updated successfully!', 'success')
                return redirect(url_for('view_rule', rule_id=rule_id))
            else:
                flash('Rule validation failed. Please check the errors.', 'error')

        except Exception as e:
            flash(f'Error updating rule: {str(e)}', 'error')

    return render_template('edit_rule.html', rule=rules_db[rule_id])

@app.route('/rules/<rule_id>/delete', methods=['POST'])
def delete_rule(rule_id):
    """Delete a rule."""
    if rule_id in rules_db:
        del rules_db[rule_id]
        rule_history.append({
            'action': 'deleted',
            'rule_id': rule_id,
            'timestamp': datetime.now().isoformat()
        })
        flash('Rule deleted successfully!', 'success')
    else:
        flash('Rule not found', 'error')

    return redirect(url_for('list_rules'))

@app.route('/validate', methods=['GET', 'POST'])
def validate_rules():
    """Validate rules page."""
    if request.method == 'POST':
        rule_ids = request.form.getlist('rule_ids')

        if not rule_ids:
            flash('No rules selected for validation', 'warning')
            return redirect(url_for('validate_rules'))

        rules_to_validate = [rules_db[rule_id] for rule_id in rule_ids if rule_id in rules_db]

        if not rules_to_validate:
            flash('Selected rules not found', 'error')
            return redirect(url_for('validate_rules'))

        # Validate rules
        report = validator.validate_comprehensive(rules_to_validate)

        return render_template('validation_results.html',
                             report=report,
                             selected_rules=rule_ids)

    # GET request - show validation form
    return render_template('validate_rules.html', rules=list(rules_db.values()))

@app.route('/deploy', methods=['GET', 'POST'])
def deploy_rules():
    """Deploy rules to environment."""
    if request.method == 'POST':
        environment = request.form['environment']
        rule_ids = request.form.getlist('rule_ids')

        if not rule_ids:
            flash('No rules selected for deployment', 'warning')
            return redirect(url_for('deploy_rules'))

        # Mock deployment process
        deployed_count = len(rule_ids)
        deployment_time = datetime.now().isoformat()

        flash(f'Successfully deployed {deployed_count} rules to {environment} environment!', 'success')

        return render_template('deployment_results.html',
                             environment=environment,
                             deployed_rules=rule_ids,
                             deployment_time=deployment_time)

    return render_template('deploy_rules.html', rules=list(rules_db.values()))

@app.route('/monitor')
def monitor_rules():
    """Monitor rule performance."""
    # Mock performance data for all rules
    performance_data = {}
    for rule_id, rule in rules_db.items():
        performance_data[rule_id] = {
            'total_signals': 45,
            'successful_trades': 32,
            'win_rate': 71.1,
            'avg_profit': 2.3,
            'avg_loss': -1.8,
            'profit_factor': 1.9,
            'last_updated': datetime.now().isoformat()
        }

    return render_template('monitor.html', performance=performance_data)

@app.route('/api/rules', methods=['GET'])
def api_get_rules():
    """API endpoint to get rules."""
    rule_type = request.args.get('type')
    status = request.args.get('status')

    rules_list = list(rules_db.values())

    # Apply filters
    if rule_type:
        rules_list = [r for r in rules_list if r.get('rule_type') == rule_type]

    if status:
        if status == 'enabled':
            rules_list = [r for r in rules_list if r.get('enabled', True)]
        elif status == 'disabled':
            rules_list = [r for r in rules_list if not r.get('enabled', True)]

    return jsonify({
        'success': True,
        'count': len(rules_list),
        'rules': rules_list
    })

@app.route('/api/rules/<rule_id>', methods=['GET'])
def api_get_rule(rule_id):
    """API endpoint to get specific rule."""
    if rule_id not in rules_db:
        return jsonify({'success': False, 'error': 'Rule not found'}), 404

    return jsonify({
        'success': True,
        'rule': rules_db[rule_id]
    })

@app.route('/api/validate', methods=['POST'])
def api_validate_rules():
    """API endpoint to validate rules."""
    data = request.get_json()

    if not data or 'rule_ids' not in data:
        return jsonify({'success': False, 'error': 'rule_ids required'}), 400

    rule_ids = data['rule_ids']
    rules_to_validate = [rules_db[rule_id] for rule_id in rule_ids if rule_id in rules_db]

    if not rules_to_validate:
        return jsonify({'success': False, 'error': 'No valid rules found'}), 404

    report = validator.validate_comprehensive(rules_to_validate)

    return jsonify({
        'success': True,
        'validation_report': {
            'total_rules': report.summary['total_rules'],
            'valid_rules': report.summary['valid_rules'],
            'invalid_rules': report.summary['invalid_rules'],
            'success_rate': report.summary['validation_success_rate'],
            'overall_status': report.summary['overall_status']
        }
    })


def create_templates():
    """Create HTML templates directory and files."""
    template_dir = Path(__file__).parent / 'templates'
    template_dir.mkdir(exist_ok=True)

    # Create base template
    base_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rule Manager - {% block title %}{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .sidebar {
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .card {
            border: none;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .status-active { color: #28a745; }
        .status-inactive { color: #6c757d; }
        .rule-type-breakout { background-color: #e3f2fd; }
        .rule-type-crp { background-color: #f3e5f5; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <div class="col-md-3 sidebar p-3">
                <h4 class="mb-4"><i class="fas fa-cogs"></i> Rule Manager</h4>
                <ul class="nav flex-column">
                    <li class="nav-item mb-2">
                        <a class="nav-link text-white" href="{{ url_for('dashboard') }}">
                            <i class="fas fa-tachometer-alt"></i> Dashboard
                        </a>
                    </li>
                    <li class="nav-item mb-2">
                        <a class="nav-link text-white" href="{{ url_for('list_rules') }}">
                            <i class="fas fa-list"></i> All Rules
                        </a>
                    </li>
                    <li class="nav-item mb-2">
                        <a class="nav-link text-white" href="{{ url_for('create_rule') }}">
                            <i class="fas fa-plus"></i> Create Rule
                        </a>
                    </li>
                    <li class="nav-item mb-2">
                        <a class="nav-link text-white" href="{{ url_for('validate_rules') }}">
                            <i class="fas fa-check-circle"></i> Validate
                        </a>
                    </li>
                    <li class="nav-item mb-2">
                        <a class="nav-link text-white" href="{{ url_for('deploy_rules') }}">
                            <i class="fas fa-rocket"></i> Deploy
                        </a>
                    </li>
                    <li class="nav-item mb-2">
                        <a class="nav-link text-white" href="{{ url_for('monitor_rules') }}">
                            <i class="fas fa-chart-line"></i> Monitor
                        </a>
                    </li>
                </ul>
            </div>

            <!-- Main Content -->
            <div class="col-md-9 p-4">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ 'danger' if category == 'error' else 'success' if category == 'success' else 'warning' }} alert-dismissible fade show" role="alert">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}

                {% block content %}{% endblock %}
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

    # Create dashboard template
    dashboard_html = """{% extends "base.html" %}

{% block title %}Dashboard{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col-md-12">
        <h2><i class="fas fa-tachometer-alt"></i> Rule Management Dashboard</h2>
        <p class="text-muted">Overview of your trading rules and system status</p>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-3">
        <div class="card">
            <div class="card-body text-center">
                <h5 class="card-title text-primary">{{ total_rules }}</h5>
                <p class="card-text">Total Rules</p>
                <i class="fas fa-file-code fa-2x text-primary"></i>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card">
            <div class="card-body text-center">
                <h5 class="card-title text-success">{{ active_rules }}</h5>
                <p class="card-text">Active Rules</p>
                <i class="fas fa-play-circle fa-2x text-success"></i>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card">
            <div class="card-body text-center">
                <h5 class="card-title text-info">{{ validated_rules }}</h5>
                <p class="card-text">Validated Rules</p>
                <i class="fas fa-check-circle fa-2x text-info"></i>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card">
            <div class="card-body text-center">
                <h5 class="card-title text-warning">{{ (total_rules - validated_rules) }}</h5>
                <p class="card-text">Need Validation</p>
                <i class="fas fa-exclamation-triangle fa-2x text-warning"></i>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h5><i class="fas fa-list"></i> Recent Rules</h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Rule ID</th>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for rule in rules[:5] %}
                            <tr>
                                <td>{{ rule.rule_id }}</td>
                                <td>{{ rule.name }}</td>
                                <td>
                                    <span class="badge bg-{{ 'primary' if rule.rule_type == 'breakout' else 'secondary' }}">
                                        {{ rule.rule_type }}
                                    </span>
                                </td>
                                <td>
                                    <span class="badge bg-{{ 'success' if rule.enabled else 'secondary' }}">
                                        {{ 'Active' if rule.enabled else 'Disabled' }}
                                    </span>
                                </td>
                                <td>
                                    <a href="{{ url_for('view_rule', rule_id=rule.rule_id) }}" class="btn btn-sm btn-outline-primary">View</a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5><i class="fas fa-history"></i> Recent Activity</h5>
            </div>
            <div class="card-body">
                {% if recent_activity %}
                    {% for activity in recent_activity %}
                    <div class="mb-2">
                        <small class="text-muted">{{ activity.timestamp[:19] }}</small><br>
                        <strong>{{ activity.action.title() }}</strong> rule <code>{{ activity.rule_id }}</code>
                    </div>
                    {% endfor %}
                {% else %}
                    <p class="text-muted">No recent activity</p>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}"""

    # Write templates to files
    with open(template_dir / 'base.html', 'w') as f:
        f.write(base_html)

    with open(template_dir / 'dashboard.html', 'w') as f:
        f.write(dashboard_html)

    print(f"Created templates in {template_dir}")


if __name__ == '__main__':
    create_templates()
    print("🎯 Rule Manager Web Interface")
    print("=" * 40)
    print("Starting web server...")
    print("Access the interface at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print()

    app.run(debug=True, host='0.0.0.0', port=5000)
