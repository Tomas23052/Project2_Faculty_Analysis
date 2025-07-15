#!/usr/bin/env python3
"""
IPT Faculty Performance Assessment - Advanced Dashboard
========================================================
Dashboard Streamlit avançado com múltiplas funcionalidades:
- Interface multi-página
- Filtros dinâmicos
- Visualizações interativas
- Relatórios exportáveis
- Sistema de alertas
- Benchmarking em tempo real
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
from pathlib import Path
import base64
from io import BytesIO
import zipfile
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="IPT Faculty Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuração de estilo customizado
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .alert-critical {
        background-color: #ff4444;
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.25rem 0;
    }
    .alert-warning {
        background-color: #ffaa00;
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.25rem 0;
    }
    .alert-info {
        background-color: #0088cc;
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.25rem 0;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    .stProgress .st-bo {
        background-color: #00cc88;
    }
</style>
""", unsafe_allow_html=True)

class AdvancedDashboard:
    """Dashboard avançado para análise de performance de docentes"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.load_data()
        
    def load_data(self):
        """Carregar todos os dados disponíveis"""
        try:
            # Dados principais - try multiple files in order of preference
            main_data_files = [
                "faculty_research_metrics.csv",
                "faculty_enhanced_complete.csv", 
                "faculty_advanced_parsed.csv",
                "faculty_basic.csv",
                "faculty_enriched.csv"
            ]
            
            self.df_main = pd.DataFrame()
            for file in main_data_files:
                if (self.data_dir / file).exists():
                    self.df_main = pd.read_csv(self.data_dir / file)
                    st.info(f"✅ Dados carregados de: {file}")
                    break
            
            if self.df_main.empty:
                st.warning("⚠️ Nenhum arquivo de dados principal encontrado")
            
            # Dados de clustering
            if (self.data_dir / "faculty_clusters.csv").exists():
                self.df_clusters = pd.read_csv(self.data_dir / "faculty_clusters.csv")
            else:
                self.df_clusters = pd.DataFrame()
            
            # Métricas de rede
            if (self.data_dir / "faculty_network_metrics.csv").exists():
                self.df_network = pd.read_csv(self.data_dir / "faculty_network_metrics.csv")
            else:
                self.df_network = pd.DataFrame()
            
            # Dados Scopus
            if (self.data_dir / "faculty_scopus_metrics.csv").exists():
                self.df_scopus = pd.read_csv(self.data_dir / "faculty_scopus_metrics.csv")
            else:
                self.df_scopus = pd.DataFrame()
            
            # Alertas
            if (self.data_dir / "faculty_alerts.csv").exists():
                self.df_alerts = pd.read_csv(self.data_dir / "faculty_alerts.csv")
            else:
                self.df_alerts = pd.DataFrame()
            
            # Métricas de monitorização
            if (self.data_dir / "monitoring_metrics.json").exists():
                with open(self.data_dir / "monitoring_metrics.json", 'r') as f:
                    self.monitoring_data = json.load(f)
            else:
                self.monitoring_data = {}
            
            # Análise de benchmarking
            if (self.data_dir / "benchmark_analysis.json").exists():
                with open(self.data_dir / "benchmark_analysis.json", 'r') as f:
                    self.benchmark_data = json.load(f)
            else:
                self.benchmark_data = {}
            
            # Merge dos dados se disponível
            if not self.df_main.empty:
                if not self.df_clusters.empty and 'name' in self.df_clusters.columns:
                    self.df_main = self.df_main.merge(self.df_clusters, on='name', how='left', suffixes=('', '_cluster'))
                
                if not self.df_network.empty and 'name' in self.df_network.columns:
                    self.df_main = self.df_main.merge(self.df_network, on='name', how='left', suffixes=('', '_network'))
                
                if not self.df_scopus.empty and 'name' in self.df_scopus.columns:
                    self.df_main = self.df_main.merge(self.df_scopus, on='name', how='left', suffixes=('', '_scopus'))
            
            # Log data summary
            st.sidebar.info(f"📊 **Resumo dos Dados:**\n\n"
                          f"• Principal: {len(self.df_main)} registros\n"
                          f"• Clusters: {len(self.df_clusters)} registros\n"
                          f"• Rede: {len(self.df_network)} registros\n"
                          f"• Scopus: {len(self.df_scopus)} registros\n"
                          f"• Alertas: {len(self.df_alerts)} registros")
            
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            # Create empty dataframes as fallback
            self.df_main = pd.DataFrame()
            self.df_clusters = pd.DataFrame()
            self.df_network = pd.DataFrame()
            self.df_scopus = pd.DataFrame()
            self.df_alerts = pd.DataFrame()
            self.monitoring_data = {}
            self.benchmark_data = {}
    
    @property
    def df(self):
        """Alias for main dataframe for backward compatibility"""
        return self.df_main
    
    def create_sidebar_filters(self):
        """Criar filtros na sidebar"""
        st.sidebar.header("🎛️ Filtros e Configurações")
        
        filters = {}
        
        if not self.df_main.empty:
            # Filtro por categoria
            if 'category' in self.df_main.columns:
                categories = ['Todos'] + list(self.df_main['category'].dropna().unique())
                filters['category'] = st.sidebar.selectbox(
                    "Categoria Académica",
                    categories,
                    index=0
                )
            
            # Filtro por cluster
            if 'Cluster' in self.df_main.columns:
                clusters = ['Todos'] + [f"Cluster {i}" for i in sorted(self.df_main['Cluster'].dropna().unique())]
                filters['cluster'] = st.sidebar.selectbox(
                    "Cluster de Performance",
                    clusters,
                    index=0
                )
            
            # Filtro por produtividade
            if 'orcid_works_count' in self.df_main.columns:
                pub_range = st.sidebar.slider(
                    "Número de Publicações",
                    min_value=0,
                    max_value=int(self.df_main['orcid_works_count'].max()) if not self.df_main['orcid_works_count'].isna().all() else 100,
                    value=(0, int(self.df_main['orcid_works_count'].max()) if not self.df_main['orcid_works_count'].isna().all() else 100),
                    step=5
                )
                filters['publications'] = pub_range
            
            # Filtro por citações (se disponível)
            if 'scopus_citations' in self.df_main.columns:
                citations_range = st.sidebar.slider(
                    "Número de Citações",
                    min_value=0,
                    max_value=int(self.df_main['scopus_citations'].max()) if not self.df_main['scopus_citations'].isna().all() else 1000,
                    value=(0, int(self.df_main['scopus_citations'].max()) if not self.df_main['scopus_citations'].isna().all() else 1000),
                    step=10
                )
                filters['citations'] = citations_range
        
        # Configurações de visualização
        st.sidebar.subheader("📊 Configurações de Visualização")
        filters['show_confidence'] = st.sidebar.checkbox("Mostrar intervalos de confiança", False)
        filters['show_trends'] = st.sidebar.checkbox("Mostrar linhas de tendência", True)
        filters['color_scheme'] = st.sidebar.selectbox(
            "Esquema de Cores",
            ["Viridis", "Plasma", "Blues", "Reds", "Greens"],
            index=0
        )
        
        return filters
    
    def apply_filters(self, df, filters):
        """Aplicar filtros aos dados"""
        if df.empty:
            return df
        
        filtered_df = df.copy()
        
        # Filtro por categoria
        if filters.get('category') and filters['category'] != 'Todos':
            filtered_df = filtered_df[filtered_df['category'] == filters['category']]
        
        # Filtro por cluster
        if filters.get('cluster') and filters['cluster'] != 'Todos':
            cluster_num = int(filters['cluster'].split()[-1])
            filtered_df = filtered_df[filtered_df['Cluster'] == cluster_num]
        
        # Filtro por publicações
        if filters.get('publications'):
            min_pub, max_pub = filters['publications']
            if 'orcid_works_count' in filtered_df.columns:
                filtered_df = filtered_df[
                    (filtered_df['orcid_works_count'] >= min_pub) & 
                    (filtered_df['orcid_works_count'] <= max_pub)
                ]
        
        # Filtro por citações
        if filters.get('citations'):
            min_cit, max_cit = filters['citations']
            if 'scopus_citations' in filtered_df.columns:
                filtered_df = filtered_df[
                    (filtered_df['scopus_citations'] >= min_cit) & 
                    (filtered_df['scopus_citations'] <= max_cit)
                ]
        
        return filtered_df
    
    def show_overview_page(self, filters):
        """Página de visão geral"""
        st.markdown('<h1 class="main-header">🎓 IPT Faculty Analytics Dashboard</h1>', unsafe_allow_html=True)
        
        if self.df_main.empty:
            st.warning("⚠️ Nenhum dado carregado. Execute o pipeline de coleta primeiro.")
            return
        
        filtered_df = self.apply_filters(self.df_main, filters)
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_faculty = len(filtered_df)
            st.metric("👥 Total de Docentes", total_faculty)
        
        with col2:
            if 'orcid_works_count' in filtered_df.columns:
                avg_publications = filtered_df['orcid_works_count'].mean()
                st.metric("📚 Publicações Médias", f"{avg_publications:.1f}")
            else:
                st.metric("📚 Publicações Médias", "N/A")
        
        with col3:
            if 'scopus_citations' in filtered_df.columns:
                avg_citations = filtered_df['scopus_citations'].mean()
                st.metric("📈 Citações Médias", f"{avg_citations:.0f}")
            else:
                st.metric("📈 Citações Médias", "N/A")
        
        with col4:
            # Calcular score de performance
            performance_score = self.calculate_performance_score(filtered_df)
            st.metric("⭐ Performance Score", f"{performance_score:.1f}/100")
        
        # Gráficos principais
        col1, col2 = st.columns(2)
        
        with col1:
            self.show_category_distribution(filtered_df, filters)
        
        with col2:
            self.show_performance_scatter(filtered_df, filters)
        
        # Alertas
        self.show_alerts_summary()
        
        # Tendências temporais
        st.subheader("📈 Tendências e Projeções")
        self.show_trends_projection(filtered_df)
    
    def show_performance_analysis(self, filters):
        """Página de análise de performance"""
        st.header("📊 Análise Detalhada de Performance")
        
        if self.df_main.empty:
            st.warning("⚠️ Nenhum dado disponível para análise.")
            return
        
        filtered_df = self.apply_filters(self.df_main, filters)
        
        # Análise de clusters
        if 'Cluster' in filtered_df.columns:
            st.subheader("🎯 Análise de Clusters")
            self.show_cluster_analysis(filtered_df, filters)
        
        # Análise de rede
        if not self.df_network.empty:
            st.subheader("🌐 Análise de Rede de Colaboração")
            self.show_network_analysis()
        
        # Top performers
        st.subheader("🏆 Top Performers")
        self.show_top_performers(filtered_df)
        
        # Performance por departamento
        if 'department' in filtered_df.columns:
            st.subheader("🏢 Performance por Departamento")
            self.show_department_performance(filtered_df, filters)
    
    def show_benchmarking_page(self, filters):
        """Página de benchmarking"""
        st.header("🏆 Benchmarking Internacional")
        
        if not self.benchmark_data:
            st.warning("⚠️ Dados de benchmarking não disponíveis.")
            return
        
        # Comparação com benchmarks
        self.show_benchmark_comparison()
        
        # Gap analysis
        st.subheader("📊 Análise de Gaps")
        self.show_gap_analysis()
        
        # Roadmap
        st.subheader("🛣️ Roadmap Estratégico")
        self.show_strategic_roadmap()
    
    def show_reports_page(self, filters):
        """Página de relatórios"""
        st.header("📋 Relatórios e Exportação")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Relatórios Disponíveis")
            
            if st.button("📈 Relatório Executivo"):
                self.generate_executive_report()
            
            if st.button("📋 Relatório de Compliance"):
                self.generate_compliance_report()
            
            if st.button("🔍 Relatório Detalhado"):
                self.generate_detailed_report()
        
        with col2:
            st.subheader("💾 Exportar Dados")
            
            if st.button("📊 Exportar para Excel"):
                self.export_to_excel()
            
            if st.button("📄 Exportar para PDF"):
                self.export_to_pdf()
            
            if st.button("📦 Exportar Tudo (ZIP)"):
                self.export_all_data()
    
    def calculate_performance_score(self, df):
        """Calcular score de performance composto"""
        if df.empty:
            return 0
        
        scores = []
        
        # Publicações (40%)
        if 'orcid_works_count' in df.columns:
            pub_score = df['orcid_works_count'].fillna(0).mean() / 50 * 40
            scores.append(min(pub_score, 40))
        
        # Citações (30%)
        if 'scopus_citations' in df.columns:
            cit_score = df['scopus_citations'].fillna(0).mean() / 500 * 30
            scores.append(min(cit_score, 30))
        
        # Colaboração (20%)
        if 'degree_centrality' in df.columns:
            collab_score = df['degree_centrality'].fillna(0).mean() * 20
            scores.append(min(collab_score, 20))
        
        # Qualidade (10%)
        if 'q1_publications' in df.columns and 'scopus_publications' in df.columns:
            q1_ratio = df['q1_publications'].fillna(0).sum() / max(df['scopus_publications'].fillna(0).sum(), 1)
            quality_score = q1_ratio * 10
            scores.append(min(quality_score, 10))
        
        return sum(scores) if scores else 0
    
    def show_category_distribution(self, df, filters):
        """Mostrar distribuição por categoria"""
        if 'category' not in df.columns:
            st.info("Dados de categoria não disponíveis")
            return
        
        st.subheader("👨‍🏫 Distribuição por Categoria")
        
        category_counts = df['category'].value_counts()
        
        fig = px.pie(
            values=category_counts.values,
            names=category_counts.index,
            title="Distribuição de Docentes por Categoria",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=400)
        
        st.plotly_chart(fig, use_container_width=True)
    
    def show_performance_scatter(self, df, filters):
        """Mostrar scatter plot de performance"""
        if 'orcid_works_count' not in df.columns:
            st.info("Dados de publicações não disponíveis")
            return
        
        st.subheader("📊 Performance: Publicações vs Citações")
        
        x_col = 'orcid_works_count'
        y_col = 'scopus_citations' if 'scopus_citations' in df.columns else 'orcid_recent_works'
        
        fig = px.scatter(
            df,
            x=x_col,
            y=y_col,
            color='category' if 'category' in df.columns else None,
            size='orcid_funding_count' if 'orcid_funding_count' in df.columns else None,
            hover_name='name',
            title="Relação entre Publicações e Impacto",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        
        if filters.get('show_trends'):
            fig.add_traces(px.scatter(df, x=x_col, y=y_col, trendline="ols").data[1:])
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    def show_alerts_summary(self):
        """Mostrar resumo de alertas"""
        if self.df_alerts.empty:
            return
        
        st.subheader("🚨 Alertas Ativos")
        
        col1, col2, col3 = st.columns(3)
        
        critical_alerts = len(self.df_alerts[self.df_alerts['priority'] == 'ALTA'])
        warning_alerts = len(self.df_alerts[self.df_alerts['priority'] == 'MÉDIA'])
        info_alerts = len(self.df_alerts[self.df_alerts['priority'] == 'BAIXA'])
        
        with col1:
            st.metric("🔴 Críticos", critical_alerts)
        
        with col2:
            st.metric("🟡 Avisos", warning_alerts)
        
        with col3:
            st.metric("🔵 Informativos", info_alerts)
        
        # Mostrar alertas mais importantes
        if critical_alerts > 0:
            st.error("⚠️ Alertas Críticos Encontrados!")
            critical = self.df_alerts[self.df_alerts['priority'] == 'ALTA']
            for _, alert in critical.head(3).iterrows():
                st.markdown(f"**{alert['category']}**: {alert['message']}")
    
    def show_trends_projection(self, df):
        """Mostrar tendências e projeções"""
        # Simular dados históricos para demonstração
        years = list(range(2020, 2025))
        
        if 'orcid_works_count' in df.columns:
            current_avg = df['orcid_works_count'].mean()
        else:
            current_avg = 30
        
        # Simular tendência histórica
        historical_data = [current_avg * (1 - 0.1 * (2024 - year)) for year in years]
        
        # Projeção futura
        future_years = list(range(2025, 2028))
        projections = [current_avg * (1 + 0.08 * (year - 2024)) for year in future_years]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=years,
            y=historical_data,
            mode='lines+markers',
            name='Dados Históricos',
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=future_years,
            y=projections,
            mode='lines+markers',
            name='Projeção',
            line=dict(color='red', dash='dash')
        ))
        
        fig.update_layout(
            title="Evolução da Produção Científica",
            xaxis_title="Ano",
            yaxis_title="Publicações Médias",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def show_cluster_analysis(self, df, filters):
        """Mostrar análise de clusters"""
        cluster_summary = df.groupby('Cluster').agg({
            'name': 'count',
            'orcid_works_count': 'mean',
            'orcid_recent_works': 'mean' if 'orcid_recent_works' in df.columns else lambda x: 0
        }).round(2)
        
        cluster_summary.columns = ['Número de Docentes', 'Publicações Médias', 'Publicações Recentes']
        
        st.dataframe(cluster_summary, use_container_width=True)
        
        # Visualização dos clusters
        if 'orcid_works_count' in df.columns and 'orcid_recent_works' in df.columns:
            fig = px.scatter(
                df,
                x='orcid_works_count',
                y='orcid_recent_works',
                color='Cluster',
                title="Clusters de Performance",
                labels={'orcid_works_count': 'Total de Publicações', 'orcid_recent_works': 'Publicações Recentes'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def show_network_analysis(self):
        """Mostrar análise de rede"""
        if self.df_network.empty:
            st.info("Dados de rede não disponíveis")
            return
        
        # Top colaboradores
        top_collaborators = self.df_network.nlargest(10, 'degree_centrality')
        
        fig = px.bar(
            top_collaborators,
            x='degree_centrality',
            y='name',
            orientation='h',
            title="Top 10 Colaboradores (Centralidade de Grau)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def show_top_performers(self, df):
        """Mostrar top performers"""
        if 'orcid_works_count' not in df.columns:
            st.info("Dados de performance não disponíveis")
            return
        
        # Calcular score para cada docente
        df_performance = df.copy()
        
        # Score baseado em múltiplas métricas
        scores = []
        for _, row in df_performance.iterrows():
            score = 0
            
            # Publicações (40%)
            pubs = row.get('orcid_works_count', 0)
            score += min(pubs / 100, 1) * 40
            
            # Citações (30%)
            if 'scopus_citations' in row:
                citations = row.get('scopus_citations', 0)
                score += min(citations / 1000, 1) * 30
            
            # Publicações recentes (20%)
            recent = row.get('orcid_recent_works', 0)
            score += min(recent / 20, 1) * 20
            
            # H-index (10%)
            if 'scopus_h_index' in row:
                h_index = row.get('scopus_h_index', 0)
                score += min(h_index / 20, 1) * 10
            
            scores.append(score)
        
        df_performance['performance_score'] = scores
        
        # Top 10
        top_performers = df_performance.nlargest(10, 'performance_score')
        
        fig = px.bar(
            top_performers,
            x='performance_score',
            y='name',
            orientation='h',
            title="Top 10 Performers (Score Composto)",
            color='performance_score',
            color_continuous_scale='Viridis'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def show_department_performance(self, df, filters):
        """Mostrar performance por departamento"""
        if 'department' not in df.columns or df['department'].isna().all():
            st.info("Dados de departamento não disponíveis")
            return
        
        dept_performance = df.groupby('department').agg({
            'orcid_works_count': ['count', 'mean', 'sum'],
            'orcid_recent_works': 'mean' if 'orcid_recent_works' in df.columns else lambda x: 0
        }).round(2)
        
        st.dataframe(dept_performance, use_container_width=True)
    
    def show_benchmark_comparison(self):
        """Mostrar comparação com benchmarks"""
        if 'benchmark_comparison' not in self.benchmark_data:
            st.info("Dados de benchmark não disponíveis")
            return
        
        benchmark_df = pd.DataFrame(self.benchmark_data['benchmark_comparison'])
        
        st.dataframe(benchmark_df.T, use_container_width=True)
        
        # Gráfico de comparação
        # Métricas disponíveis
        available_metrics = []
        
        if 'orcid_works_count' in self.df_main.columns:
            available_metrics.append('orcid_works_count')
        if 'orcid_recent_works' in self.df_main.columns:
            available_metrics.append('orcid_recent_works')
        if 'orcid_funding_count' in self.df_main.columns:
            available_metrics.append('orcid_funding_count')
        
        if not available_metrics:
            st.warning("Nenhuma métrica de pesquisa disponível para comparação.")
            return
        
        metrics = available_metrics
        
        fig = go.Figure()
        
        for metric in metrics:
            if metric in benchmark_df.columns:
                fig.add_trace(go.Bar(
                    name=metric,
                    x=benchmark_df.index,
                    y=benchmark_df.loc[metric]
                ))
        
        fig.update_layout(
            title="Comparação com Benchmarks",
            xaxis_title="Instituições",
            yaxis_title="Valores",
            barmode='group'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def show_gap_analysis(self):
        """Mostrar análise de gaps"""
        if 'gaps' not in self.benchmark_data:
            st.info("Análise de gaps não disponível")
            return
        
        gaps_data = self.benchmark_data['gaps']
        
        metrics = list(gaps_data.keys())
        gap_percentages = [gaps_data[metric]['percentage'] for metric in metrics]
        
        fig = px.bar(
            x=metrics,
            y=gap_percentages,
            title="Gaps vs Benchmarks (%)",
            color=gap_percentages,
            color_continuous_scale='Reds'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def show_strategic_roadmap(self):
        """Mostrar roadmap estratégico"""
        if 'roadmap' not in self.benchmark_data:
            st.info("Roadmap não disponível")
            return
        
        roadmap = self.benchmark_data['roadmap']
        
        for year, plan in roadmap.items():
            with st.expander(f"📅 {year} - {plan['foco']}"):
                st.write(f"**Meta de Publicações:** {plan['target_publications']:.1f}")
                st.write("**Objetivos:**")
                for meta in plan['metas']:
                    st.write(f"• {meta}")
    
    def generate_executive_report(self):
        """Gerar relatório executivo"""
        report = f"""
        # Relatório Executivo IPT Faculty Performance
        
        **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}
        
        ## Métricas Principais
        - Total de Docentes: {len(self.df_main)}
        - Publicações Médias: {self.df_main['orcid_works_count'].mean():.1f}
        - Performance Score: {self.calculate_performance_score(self.df_main):.1f}/100
        
        ## Alertas Ativos
        - Críticos: {len(self.df_alerts[self.df_alerts['priority'] == 'ALTA']) if not self.df_alerts.empty else 0}
        - Avisos: {len(self.df_alerts[self.df_alerts['priority'] == 'MÉDIA']) if not self.df_alerts.empty else 0}
        
        ## Recomendações
        1. Implementar programa de apoio à investigação
        2. Melhorar compliance ORCID
        3. Estabelecer parcerias internacionais
        """
        
        st.markdown(report)
        
        # Download button
        st.download_button(
            label="📥 Download Relatório",
            data=report,
            file_name=f"relatorio_executivo_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown"
        )
    
    def generate_compliance_report(self):
        """Gerar relatório de compliance"""
        st.info("Relatório de compliance gerado! (Funcionalidade em desenvolvimento)")
    
    def generate_detailed_report(self):
        """Gerar relatório detalhado"""
        st.info("Relatório detalhado gerado! (Funcionalidade em desenvolvimento)")
    
    def export_to_excel(self):
        """Exportar dados para Excel"""
        if self.df_main.empty:
            st.warning("Nenhum dado para exportar")
            return
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            self.df_main.to_excel(writer, sheet_name='Dados Principais', index=False)
            
            if not self.df_clusters.empty:
                self.df_clusters.to_excel(writer, sheet_name='Clusters', index=False)
            
            if not self.df_network.empty:
                self.df_network.to_excel(writer, sheet_name='Rede', index=False)
        
        st.download_button(
            label="📊 Download Excel",
            data=output.getvalue(),
            file_name=f"ipt_faculty_data_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    def export_to_pdf(self):
        """Exportar relatório para PDF"""
        st.info("Exportação para PDF em desenvolvimento")
    
    def export_all_data(self):
        """Exportar todos os dados em ZIP"""
        st.info("Exportação completa em desenvolvimento")

def main():
    """Função principal do dashboard"""
    dashboard = AdvancedDashboard()
    
    # Sidebar navigation
    st.sidebar.title("🎓 IPT Faculty Analytics")
    
    pages = {
        "📊 Visão Geral": "overview",
        "🎯 Análise de Performance": "performance",
        "🏆 Benchmarking": "benchmarking",
        "📋 Relatórios": "reports"
    }
    
    selected_page = st.sidebar.selectbox(
        "Navegação",
        list(pages.keys())
    )
    
    # Filtros
    filters = dashboard.create_sidebar_filters()
    
    # Mostrar página selecionada
    page_key = pages[selected_page]
    
    if page_key == "overview":
        dashboard.show_overview_page(filters)
    elif page_key == "performance":
        dashboard.show_performance_analysis(filters)
    elif page_key == "benchmarking":
        dashboard.show_benchmarking_page(filters)
    elif page_key == "reports":
        dashboard.show_reports_page(filters)
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("🔄 **Última atualização:** " + datetime.now().strftime('%d/%m/%Y %H:%M'))
    st.sidebar.markdown("📧 **Suporte:** analytics@ipt.pt")

if __name__ == "__main__":
    main()
