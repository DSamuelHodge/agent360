package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gorilla/mux"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/redis/go-redis/v9"
	"github.com/spf13/viper"
	"go.uber.org/zap"
)

var (
	logger *zap.Logger
	rdb    *redis.Client
)

func init() {
	// Initialize logger
	var err error
	logger, err = zap.NewProduction()
	if err != nil {
		log.Fatalf("Failed to initialize logger: %v", err)
	}
	defer logger.Sync()

	// Load configuration
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./config")
	viper.AddConfigPath(".")

	if err := viper.ReadInConfig(); err != nil {
		logger.Error("Failed to read config file", zap.Error(err))
	}

	// Initialize Redis
	rdb = redis.NewClient(&redis.Options{
		Addr:     viper.GetString("redis.addr"),
		Password: viper.GetString("redis.password"),
		DB:       viper.GetInt("redis.db"),
	})
}

func main() {
	r := mux.NewRouter()

	// Health check endpoints
	r.HandleFunc("/health", healthCheckHandler).Methods("GET")
	r.HandleFunc("/ready", readinessCheckHandler).Methods("GET")

	// Metrics endpoint
	r.Handle("/metrics", promhttp.Handler())

	// API routes
	api := r.PathPrefix("/api/v1").Subrouter()
	api.HandleFunc("/agents", listAgentsHandler).Methods("GET")
	api.HandleFunc("/agents/{id}", getAgentHandler).Methods("GET")
	api.HandleFunc("/agents/{id}/tasks", getAgentTasksHandler).Methods("GET")

	// Create HTTP server
	srv := &http.Server{
		Addr:         fmt.Sprintf(":%d", viper.GetInt("server.port")),
		Handler:      r,
		ReadTimeout:  time.Duration(viper.GetInt("server.readTimeout")) * time.Second,
		WriteTimeout: time.Duration(viper.GetInt("server.writeTimeout")) * time.Second,
	}

	// Start server in a goroutine
	go func() {
		logger.Info("Starting server", zap.String("addr", srv.Addr))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("Failed to start server", zap.Error(err))
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	// Graceful shutdown
	logger.Info("Server is shutting down...")
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		logger.Fatal("Server forced to shutdown", zap.Error(err))
	}

	logger.Info("Server exited properly")
}

// Handler functions
func healthCheckHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "healthy")
}

func readinessCheckHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	err := rdb.Ping(ctx).Err()
	if err != nil {
		w.WriteHeader(http.StatusServiceUnavailable)
		fmt.Fprintf(w, "not ready: %v", err)
		return
	}
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "ready")
}

func listAgentsHandler(w http.ResponseWriter, r *http.Request) {
	// TODO: Implement agent listing
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "[]")
}

func getAgentHandler(w http.ResponseWriter, r *http.Request) {
	// TODO: Implement single agent retrieval
	vars := mux.Vars(r)
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "{\"id\": \"%s\"}", vars["id"])
}

func getAgentTasksHandler(w http.ResponseWriter, r *http.Request) {
	// TODO: Implement agent tasks retrieval
	vars := mux.Vars(r)
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "{\"agent_id\": \"%s\", \"tasks\": []}", vars["id"])
}
